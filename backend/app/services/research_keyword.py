from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError
import uuid
import math

from app.models import ResearchKeyword, BrainstormSession, Lab, LabMember
from app.schemas.research_keyword import (
    ResearchKeywordCreate, ResearchKeywordUpdate, ResearchKeywordResponse,
    ResearchKeywordListResponse, BulkKeywordCreate, BulkKeywordDelete,
    BulkOperationResult, SessionKeywordStats, KeywordSourceStats
)
from app.utils.exceptions import NotFoundError, AuthorizationError, ValidationError, ConflictError
from app.utils.permissions import LabPermissions


class ResearchKeywordService:
    def __init__(self, db: Session):
        self.db = db

    async def create_keyword(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: ResearchKeywordCreate,
        upsert: bool = False
    ) -> Tuple[ResearchKeywordResponse, bool]:
        """
        Create a new research keyword (Editor+ required)
        Returns (keyword, is_created) tuple
        """
        # Check session exists and user has editor+ permissions
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        # Check if keyword already exists (case-insensitive)
        existing = self.db.query(ResearchKeyword).filter(
            and_(
                ResearchKeyword.session_id == session_id,
                func.lower(ResearchKeyword.term) == request.term.lower()
            )
        ).first()

        if existing:
            if upsert:
                # Update existing keyword
                if request.weight is not None:
                    existing.weight = request.weight
                if request.source:
                    existing.source = request.source
                    if request.source == "user":
                        existing.approved_by_user = True
                if request.rationale is not None:
                    existing.rationale = request.rationale
                if request.is_primary is not None:
                    existing.is_primary = request.is_primary
                if request.approved_by_user is not None:
                    existing.approved_by_user = request.approved_by_user

                self.db.commit()
                self.db.refresh(existing)
                return await self._keyword_to_response(existing), False
            else:
                raise ConflictError(f"Keyword '{request.term}' already exists in this session")

        # Create new keyword
        keyword = ResearchKeyword(
            session_id=session_id,
            term=request.term.lower(),  # Normalize to lowercase
            weight=request.weight,
            source=request.source,
            rationale=request.rationale,
            is_primary=request.is_primary,
            approved_by_user=(
                request.approved_by_user
                if request.approved_by_user is not None
                else request.source == "user"
            )
        )

        try:
            self.db.add(keyword)
            self.db.commit()
            self.db.refresh(keyword)
            return await self._keyword_to_response(keyword), True
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(f"Keyword '{request.term}' already exists in this session")

    async def bulk_create_keywords(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: BulkKeywordCreate
    ) -> BulkOperationResult:
        """Bulk create/update keywords (Editor+ required)"""
        # Check session exists and user has editor+ permissions
        await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        result = BulkOperationResult()
        
        # Get existing keywords for duplicate checking
        existing_terms = {
            kw.term.lower(): kw for kw in 
            self.db.query(ResearchKeyword).filter(
                ResearchKeyword.session_id == session_id
            ).all()
        }

        for item in request.items:
            try:
                normalized_term = item.term.lower()
                
                if normalized_term in existing_terms:
                    existing_keyword = existing_terms[normalized_term]
                    
                    if request.mode == "skip":
                        result.skipped += 1
                        result.duplicates.append(item.term)
                        continue
                    elif request.mode == "upsert":
                        # Update existing
                        if item.weight is not None:
                            existing_keyword.weight = item.weight
                        if item.source:
                            existing_keyword.source = item.source
                            if item.source == "user":
                                existing_keyword.approved_by_user = True
                        if item.rationale is not None:
                            existing_keyword.rationale = item.rationale
                        if item.is_primary is not None:
                            existing_keyword.is_primary = item.is_primary
                        if item.approved_by_user is not None:
                            existing_keyword.approved_by_user = item.approved_by_user
                        result.updated += 1
                    elif request.mode == "merge":
                        # Merge logic: keep higher weight, combine rationale
                        if item.weight and (not existing_keyword.weight or item.weight > existing_keyword.weight):
                            existing_keyword.weight = item.weight
                        if item.rationale and existing_keyword.rationale:
                            existing_keyword.rationale = f"{existing_keyword.rationale}; {item.rationale}"
                        elif item.rationale and not existing_keyword.rationale:
                            existing_keyword.rationale = item.rationale
                        if item.is_primary:
                            existing_keyword.is_primary = True
                        if item.approved_by_user:
                            existing_keyword.approved_by_user = True
                        result.updated += 1
                else:
                    # Create new keyword
                    keyword = ResearchKeyword(
                        session_id=session_id,
                        term=normalized_term,
                        weight=item.weight,
                        source=item.source,
                        rationale=item.rationale,
                        is_primary=item.is_primary,
                        approved_by_user=(
                            item.approved_by_user
                            if item.approved_by_user is not None
                            else item.source == "user"
                        )
                    )
                    self.db.add(keyword)
                    existing_terms[normalized_term] = keyword
                    result.created += 1

            except Exception as e:
                result.errors.append({
                    "term": item.term,
                    "error": str(e)
                })

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            result.errors.append({"error": f"Database constraint violation: {str(e)}"})

        return result

    async def list_session_keywords(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        source: Optional[str] = None,
        is_primary: Optional[bool] = None,
        approved_by_user: Optional[bool] = None,
        q: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        limit: int = 50
    ) -> ResearchKeywordListResponse:
        """List keywords in session (Viewer+ required)"""
        # Check session exists and user has access
        await self._get_session_with_permissions(
            current_user_id, session_id, "view_data"
        )

        # Build query
        query = self.db.query(ResearchKeyword).filter(
            ResearchKeyword.session_id == session_id
        )

        # Apply filters
        if source:
            query = query.filter(ResearchKeyword.source == source)
        
        if is_primary is not None:
            query = query.filter(ResearchKeyword.is_primary == is_primary)

        if approved_by_user is not None:
            query = query.filter(ResearchKeyword.approved_by_user == approved_by_user)

        if q:
            search_filter = or_(
                ResearchKeyword.term.ilike(f"%{q}%"),
                ResearchKeyword.rationale.ilike(f"%{q}%")
            )
            query = query.filter(search_filter)

        # Apply sorting
        sort_column = getattr(ResearchKeyword, sort, ResearchKeyword.created_at)
        if order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        keywords = query.offset(offset).limit(limit).all()

        # Convert to responses
        items = []
        for keyword in keywords:
            response = await self._keyword_to_response(keyword)
            items.append(response)

        total_pages = math.ceil(total / limit) if total > 0 else 1

        return ResearchKeywordListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    async def get_keyword(
        self,
        current_user_id: uuid.UUID,
        keyword_id: uuid.UUID
    ) -> ResearchKeywordResponse:
        """Get keyword details (Viewer+ required)"""
        keyword = await self._get_keyword_with_permissions(
            current_user_id, keyword_id, "view_data"
        )
        return await self._keyword_to_response(keyword)

    async def update_keyword(
        self,
        current_user_id: uuid.UUID,
        keyword_id: uuid.UUID,
        request: ResearchKeywordUpdate
    ) -> ResearchKeywordResponse:
        """Update keyword (Editor+ required)"""
        keyword = await self._get_keyword_with_permissions(
            current_user_id, keyword_id, "create_brainstorm"
        )

        # Check for term uniqueness if term is being updated
        if request.term and request.term.lower() != keyword.term.lower():
            existing = self.db.query(ResearchKeyword).filter(
                and_(
                    ResearchKeyword.session_id == keyword.session_id,
                    func.lower(ResearchKeyword.term) == request.term.lower(),
                    ResearchKeyword.id != keyword_id
                )
            ).first()
            
            if existing:
                raise ConflictError(f"Keyword '{request.term}' already exists in this session")

        # Update fields
        if request.term is not None:
            keyword.term = request.term.lower()
        if request.weight is not None:
            keyword.weight = request.weight
        if request.source is not None:
            keyword.source = request.source
        if request.rationale is not None:
            keyword.rationale = request.rationale
        if request.is_primary is not None:
            keyword.is_primary = request.is_primary
        if request.approved_by_user is not None:
            keyword.approved_by_user = request.approved_by_user

        try:
            self.db.commit()
            self.db.refresh(keyword)
            return await self._keyword_to_response(keyword)
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(f"Keyword '{request.term}' already exists in this session")

    async def approve_keyword(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        keyword_id: uuid.UUID
    ) -> ResearchKeywordResponse:
        """Mark a keyword as approved by a user (Editor+ required)"""
        await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        keyword = self.db.query(ResearchKeyword).filter(
            and_(
                ResearchKeyword.id == keyword_id,
                ResearchKeyword.session_id == session_id
            )
        ).first()

        if not keyword:
            raise NotFoundError("Research keyword not found")

        if not keyword.approved_by_user:
            keyword.approved_by_user = True

        self.db.commit()
        self.db.refresh(keyword)
        return await self._keyword_to_response(keyword)

    async def delete_keyword(
        self,
        current_user_id: uuid.UUID,
        keyword_id: uuid.UUID
    ) -> None:
        """Delete keyword (Editor+ required)"""
        keyword = await self._get_keyword_with_permissions(
            current_user_id, keyword_id, "create_brainstorm"
        )

        self.db.delete(keyword)
        self.db.commit()

    async def bulk_delete_keywords(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: BulkKeywordDelete
    ) -> BulkOperationResult:
        """Bulk delete keywords (Editor+ required)"""
        # Check session exists and user has editor+ permissions
        await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        result = BulkOperationResult()

        # Get keywords to delete
        keywords = self.db.query(ResearchKeyword).filter(
            and_(
                ResearchKeyword.session_id == session_id,
                ResearchKeyword.id.in_(request.ids)
            )
        ).all()

        found_ids = {kw.id for kw in keywords}
        result.not_found = len(request.ids) - len(found_ids)

        # Delete found keywords
        for keyword in keywords:
            try:
                self.db.delete(keyword)
                result.deleted += 1
            except Exception as e:
                result.errors.append({
                    "keyword_id": str(keyword.id),
                    "error": str(e)
                })

        self.db.commit()
        return result

    async def get_session_keyword_stats(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> SessionKeywordStats:
        """Get keyword statistics for session (Viewer+ required)"""
        # Check session exists and user has access
        await self._get_session_with_permissions(
            current_user_id, session_id, "view_data"
        )

        keywords = self.db.query(ResearchKeyword).filter(
            ResearchKeyword.session_id == session_id
        ).all()

        total_keywords = len(keywords)
        primary_keywords = sum(1 for kw in keywords if kw.is_primary)
        approved_keywords = sum(1 for kw in keywords if kw.approved_by_user)
        pending_keywords = total_keywords - approved_keywords

        # Source statistics
        source_stats = KeywordSourceStats()
        for keyword in keywords:
            if keyword.source == "user":
                source_stats.user += 1
            elif keyword.source == "ai":
                source_stats.ai += 1
            elif keyword.source == "imported":
                source_stats.imported += 1

        # Weight statistics
        weights = [kw.weight for kw in keywords if kw.weight is not None]
        avg_weight = sum(weights) / len(weights) if weights else None

        # Weight distribution
        weight_distribution = {}
        if weights:
            for weight in weights:
                if weight < 0.2:
                    bucket = "0.0-0.2"
                elif weight < 0.4:
                    bucket = "0.2-0.4"
                elif weight < 0.6:
                    bucket = "0.4-0.6"
                elif weight < 0.8:
                    bucket = "0.6-0.8"
                else:
                    bucket = "0.8-1.0"
                weight_distribution[bucket] = weight_distribution.get(bucket, 0) + 1

        return SessionKeywordStats(
            total_keywords=total_keywords,
            primary_keywords=primary_keywords,
            by_source=source_stats,
            approved_keywords=approved_keywords,
            pending_keywords=pending_keywords,
            avg_weight=avg_weight,
            weight_distribution=weight_distribution
        )

    # Helper methods
    async def _get_session_with_permissions(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        required_permission: str
    ) -> BrainstormSession:
        """Get session and check permissions"""
        session = self.db.query(BrainstormSession).options(
            joinedload(BrainstormSession.lab)
        ).filter(
            and_(
                BrainstormSession.id == session_id,
                BrainstormSession.deleted_at.is_(None)
            )
        ).first()

        if not session:
            raise NotFoundError("Brainstorm session not found")

        # Check permissions
        user_role = await self._get_user_lab_role(current_user_id, session.lab_id)
        if not user_role or not LabPermissions.can_perform(user_role, required_permission):
            raise AuthorizationError(f"Insufficient permissions for {required_permission}")

        return session

    async def _get_keyword_with_permissions(
        self,
        current_user_id: uuid.UUID,
        keyword_id: uuid.UUID,
        required_permission: str
    ) -> ResearchKeyword:
        """Get keyword and check permissions"""
        keyword = self.db.query(ResearchKeyword).options(
            joinedload(ResearchKeyword.session).joinedload(BrainstormSession.lab)
        ).filter(ResearchKeyword.id == keyword_id).first()

        if not keyword:
            raise NotFoundError("Research keyword not found")

        if keyword.session.deleted_at:
            raise NotFoundError("Research keyword not found")

        # Check permissions
        user_role = await self._get_user_lab_role(current_user_id, keyword.session.lab_id)
        if not user_role or not LabPermissions.can_perform(user_role, required_permission):
            raise AuthorizationError(f"Insufficient permissions for {required_permission}")

        return keyword

    async def _get_user_lab_role(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> Optional[str]:
        """Get user's role in lab"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()

        if not lab:
            return None

        # Check if owner
        if lab.owner_id == user_id:
            return "owner"

        # Check member role
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id)
        ).first()

        return member.role if member else None

    async def _keyword_to_response(self, keyword: ResearchKeyword) -> ResearchKeywordResponse:
        """Convert keyword to response"""
        return ResearchKeywordResponse(
            id=keyword.id,
            session_id=keyword.session_id,
            term=keyword.term,
            weight=keyword.weight,
            source=keyword.source,
            rationale=keyword.rationale,
            is_primary=keyword.is_primary,
            approved_by_user=keyword.approved_by_user,
            created_at=keyword.created_at
        )
