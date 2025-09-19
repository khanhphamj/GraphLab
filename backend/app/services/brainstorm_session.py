from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
import uuid
import math

from app.models import BrainstormSession, Lab, User, ResearchKeyword, LabMember
from app.schemas.brainstorm_session import (
    BrainstormSessionCreate,
    BrainstormSessionUpdate,
    BrainstormSessionResponse,
    BrainstormSessionListResponse,
    KeywordStats,
    CrawlRequest,
    ConversationTurn,
    ConversationUpdate,
)
from app.utils.exceptions import NotFoundError, AuthorizationError, ValidationError
from app.utils.permissions import LabPermissions


class BrainstormSessionService:
    def __init__(self, db: Session):
        self.db = db

    async def create_session(
        self, 
        current_user_id: uuid.UUID, 
        lab_id: uuid.UUID, 
        request: BrainstormSessionCreate
    ) -> BrainstormSessionResponse:
        """Create a new brainstorm session (Editor+ required)"""
        # Check lab exists and user has editor+ permissions
        if not await self._user_can_create_brainstorm(current_user_id, lab_id):
            raise AuthorizationError("Insufficient permissions to create brainstorm sessions")

        # Create session
        session = BrainstormSession(
            lab_id=lab_id,
            created_by=current_user_id,
            title=request.title,
            description=request.description,
            status=request.status,
            session_data=request.session_data
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return await self._session_to_response(session)

    async def get_session(
        self, 
        current_user_id: uuid.UUID, 
        session_id: uuid.UUID, 
        expand_stats: bool = False
    ) -> BrainstormSessionResponse:
        """Get session details (Viewer+ required)"""
        session = await self._get_session_with_permissions(current_user_id, session_id, "view_data")
        return await self._session_to_response(session, expand_stats=expand_stats)

    async def list_lab_sessions(
        self,
        current_user_id: uuid.UUID,
        lab_id: uuid.UUID,
        status: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc"
    ) -> BrainstormSessionListResponse:
        """List sessions in lab (Viewer+ required)"""
        # Check lab access
        if not await self._user_has_lab_access(current_user_id, lab_id):
            raise AuthorizationError("Access denied to this lab")

        # Build query
        query = self.db.query(BrainstormSession).filter(
            and_(
                BrainstormSession.lab_id == lab_id,
                BrainstormSession.deleted_at.is_(None)
            )
        )

        # Apply filters
        if status:
            query = query.filter(BrainstormSession.status == status)

        if q:
            search_filter = or_(
                BrainstormSession.title.ilike(f"%{q}%"),
                BrainstormSession.description.ilike(f"%{q}%")
            )
            query = query.filter(search_filter)

        # Apply sorting
        sort_column = getattr(BrainstormSession, sort, BrainstormSession.created_at)
        if order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        sessions = query.offset(offset).limit(limit).all()

        # Convert to responses
        items = []
        for session in sessions:
            response = await self._session_to_response(session)
            items.append(response)

        total_pages = math.ceil(total / limit) if total > 0 else 1

        return BrainstormSessionListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    async def update_session(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: BrainstormSessionUpdate
    ) -> BrainstormSessionResponse:
        """Update session (Editor+ required)"""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        # Update fields
        if request.title is not None:
            session.title = request.title
        if request.description is not None:
            session.description = request.description
        if request.status is not None:
            session.status = request.status
        if request.session_data is not None:
            session.session_data = request.session_data

        session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)

        return await self._session_to_response(session)

    async def append_conversation_turn(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: ConversationUpdate
    ) -> BrainstormSessionResponse:
        """Append a conversation turn to the session."""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "participate_conversations"
        )

        session_data: Dict[str, Any] = dict(session.session_data or {})
        existing_conversation = session_data.get("conversation")

        if isinstance(existing_conversation, list):
            conversation_history = list(existing_conversation)
        else:
            conversation_history = []

        turn = ConversationTurn(**request.dict())
        turn_payload = turn.dict()
        turn_payload["timestamp"] = turn_payload["timestamp"].isoformat()

        conversation_history.append(turn_payload)
        session_data["conversation"] = conversation_history

        session.session_data = session_data
        session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)

        return await self._session_to_response(session)

    async def delete_session(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> None:
        """Soft delete session (Editor+ required)"""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        session.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    # Action methods
    async def finalize_session(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> BrainstormSessionResponse:
        """Finalize/lock session (Editor+ required)"""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        # Update session data to mark as finalized
        session_data = session.session_data or {}
        session_data["finalized"] = True
        session_data["finalized_at"] = datetime.now(timezone.utc).isoformat()
        session_data["finalized_by"] = str(current_user_id)
        
        session.session_data = session_data
        session.status = "completed"
        session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)

        return await self._session_to_response(session)

    async def archive_session(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> BrainstormSessionResponse:
        """Archive session (Editor+ required)"""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        session.status = "archived"
        session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)

        return await self._session_to_response(session)

    async def unarchive_session(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> BrainstormSessionResponse:
        """Unarchive session (Editor+ required)"""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "create_brainstorm"
        )

        session.status = "active"
        session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)

        return await self._session_to_response(session)

    async def clone_session(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> BrainstormSessionResponse:
        """Clone session with keywords (Editor+ required)"""
        original_session = await self._get_session_with_permissions(
            current_user_id, session_id, "view_data"
        )

        # Check if user can create in the lab
        if not await self._user_can_create_brainstorm(current_user_id, original_session.lab_id):
            raise AuthorizationError("Insufficient permissions to create brainstorm sessions")

        # Create new session
        new_session = BrainstormSession(
            lab_id=original_session.lab_id,
            created_by=current_user_id,
            title=f"{original_session.title} (Copy)",
            description=original_session.description,
            status="active",
            session_data=original_session.session_data.copy() if original_session.session_data else None
        )
        
        self.db.add(new_session)
        self.db.flush()  # Get the ID without committing

        # Copy keywords
        original_keywords = self.db.query(ResearchKeyword).filter(
            ResearchKeyword.session_id == session_id
        ).all()

        for keyword in original_keywords:
            new_keyword = ResearchKeyword(
                session_id=new_session.id,
                term=keyword.term,
                weight=keyword.weight,
                source=keyword.source,
                rationale=keyword.rationale,
                is_primary=keyword.is_primary
            )
            self.db.add(new_keyword)

        self.db.commit()
        self.db.refresh(new_session)

        return await self._session_to_response(new_session)

    async def kickoff_crawl(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: CrawlRequest
    ) -> Dict[str, Any]:
        """Start crawling job from session keywords (Editor+ with can_run_jobs required)"""
        session = await self._get_session_with_permissions(
            current_user_id, session_id, "run_jobs"
        )

        # Get keywords for crawling
        keyword_query = self.db.query(ResearchKeyword).filter(
            ResearchKeyword.session_id == session_id
        )
        
        if request.primary_only:
            keyword_query = keyword_query.filter(ResearchKeyword.is_primary == True)

        keywords = keyword_query.all()
        
        if not keywords:
            raise ValidationError("No keywords found for crawling")

        # TODO: Create processing job here
        # This would integrate with your job processing system
        
        return {
            "message": "Crawl job created successfully",
            "session_id": session_id,
            "keywords_count": len(keywords),
            "config": {
                "providers": request.providers,
                "categories": request.categories,
                "primary_only": request.primary_only,
                "max_results": request.max_results,
                "date_range": request.date_range
            }
        }

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

    async def _user_has_lab_access(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user has any access to lab"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()
        
        if not lab:
            return False

        # Check if owner
        if lab.owner_id == user_id:
            return True

        # Check if member
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id)
        ).first()
        
        return member is not None

    async def _user_can_create_brainstorm(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user can create brainstorm sessions"""
        user_role = await self._get_user_lab_role(user_id, lab_id)
        return user_role and LabPermissions.can_perform(user_role, "create_brainstorm")

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

    async def _session_to_response(
        self, 
        session: BrainstormSession, 
        expand_stats: bool = False
    ) -> BrainstormSessionResponse:
        """Convert session to response with optional stats"""
        # Load creator info if not already loaded
        if not hasattr(session, 'created_by_user') or session.created_by_user is None:
            creator = self.db.query(User).filter(User.id == session.created_by).first()
        else:
            creator = session.created_by_user

        response_data = {
            "id": session.id,
            "lab_id": session.lab_id,
            "created_by": session.created_by,
            "title": session.title,
            "description": session.description,
            "status": session.status,
            "session_data": session.session_data,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "creator_name": creator.name if creator else None,
            "creator_email": creator.email if creator else None
        }

        if expand_stats:
            stats = await self._get_session_stats(session.id)
            response_data["stats"] = stats

        return BrainstormSessionResponse(**response_data)

    async def _get_session_stats(self, session_id: uuid.UUID) -> KeywordStats:
        """Get keyword statistics for session"""
        keywords = self.db.query(ResearchKeyword).filter(
            ResearchKeyword.session_id == session_id
        ).all()

        total = len(keywords)
        primary_count = sum(1 for k in keywords if k.is_primary)
        
        by_source = {}
        for keyword in keywords:
            by_source[keyword.source] = by_source.get(keyword.source, 0) + 1

        return KeywordStats(
            keywords_total=total,
            primary_count=primary_count,
            by_source=by_source
        )