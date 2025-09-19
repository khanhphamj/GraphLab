from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid

from app.models import Lab, LabMember, User, KgSchema, Neo4jConnection
from app.schemas.lab import LabCreate, LabUpdate, LabResponse, LabListResponse, ActivateSchemaRequest, ActivateConnectionRequest
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError


class LabService:
    def __init__(self, db: Session):
        self.db = db

    async def create_lab(self, user_id: uuid.UUID, request: LabCreate) -> LabResponse:
        """Create a new lab"""
        # Check if lab name already exists for this user
        existing_lab = self.db.query(Lab).filter(
            and_(Lab.owner_id == user_id, Lab.name == request.name, Lab.deleted_at.is_(None))
        ).first()
        
        if existing_lab:
            raise ConflictError("Lab with this name already exists")

        # Create new lab
        lab = Lab(
            name=request.name,
            description=request.description,
            research_domain=request.research_domain,
            settings=request.settings,
            owner_id=user_id
        )
        
        self.db.add(lab)
        self.db.commit()
        self.db.refresh(lab)

        return LabResponse.from_orm(lab)

    async def get_user_labs(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> LabListResponse:
        """Get labs that user owns or is a member of"""
        # Base query for labs user has access to
        query = self.db.query(Lab).filter(
            and_(
                Lab.deleted_at.is_(None),
                or_(
                    Lab.owner_id == user_id,  # Labs user owns
                    Lab.id.in_(  # Labs user is a member of
                        self.db.query(LabMember.lab_id).filter(LabMember.user_id == user_id)
                    )
                )
            )
        )

        # Status filter
        if status:
            query = query.filter(Lab.status == status)

        # Search filter
        if q:
            search_filter = or_(
                Lab.name.ilike(f"%{q}%"),
                Lab.description.ilike(f"%{q}%"),
                Lab.research_domain.ilike(f"%{q}%")
            )
            query = query.filter(search_filter)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        labs = query.order_by(Lab.updated_at.desc()).offset(offset).limit(limit).all()

        # Calculate pagination info
        has_next = offset + limit < total
        has_prev = page > 1

        return LabListResponse(
            labs=[LabResponse.from_orm(lab) for lab in labs],
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev
        )

    async def get_lab_by_id(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> LabResponse:
        """Get lab by ID (must be owner or member)"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()

        if not lab:
            raise NotFoundError("Lab not found")

        # Check if user has access (owner or member)
        if not await self._user_has_lab_access(user_id, lab_id):
            raise AuthorizationError("Access denied")

        return LabResponse.from_orm(lab)

    async def update_lab(self, user_id: uuid.UUID, lab_id: uuid.UUID, request: LabUpdate) -> LabResponse:
        """Update lab (must be owner or admin member)"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()

        if not lab:
            raise NotFoundError("Lab not found")

        # Check if user can update (owner or admin member)
        if not await self._user_can_manage_lab(user_id, lab_id):
            raise AuthorizationError("Insufficient permissions")

        # Update fields
        if request.name is not None:
            # Check name uniqueness for this owner
            existing_lab = self.db.query(Lab).filter(
                and_(
                    Lab.owner_id == lab.owner_id,
                    Lab.name == request.name,
                    Lab.id != lab_id,
                    Lab.deleted_at.is_(None)
                )
            ).first()
            if existing_lab:
                raise ConflictError("Lab with this name already exists")
            lab.name = request.name

        if request.description is not None:
            lab.description = request.description
        if request.research_domain is not None:
            lab.research_domain = request.research_domain
        if request.settings is not None:
            lab.settings = request.settings
        if request.status is not None:
            lab.status = request.status

        lab.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(lab)

        return LabResponse.from_orm(lab)

    async def delete_lab(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> None:
        """Soft delete lab (must be owner)"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()

        if not lab:
            raise NotFoundError("Lab not found")

        # Only owner can delete
        if lab.owner_id != user_id:
            raise AuthorizationError("Only lab owner can delete the lab")

        # Soft delete
        lab.deleted_at = datetime.now(timezone.utc)
        lab.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    async def activate_schema(self, user_id: uuid.UUID, lab_id: uuid.UUID, request: ActivateSchemaRequest) -> LabResponse:
        """Activate a schema for the lab"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()

        if not lab:
            raise NotFoundError("Lab not found")

        # Check if user can manage lab
        if not await self._user_can_manage_lab(user_id, lab_id):
            raise AuthorizationError("Insufficient permissions")

        # Check if schema exists and belongs to this lab
        schema = self.db.query(KgSchema).filter(
            and_(KgSchema.id == request.schema_id, KgSchema.lab_id == lab_id)
        ).first()

        if not schema:
            raise NotFoundError("Schema not found or doesn't belong to this lab")

        # Activate schema
        lab.active_schema_id = request.schema_id
        lab.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(lab)

        return LabResponse.from_orm(lab)

    async def activate_connection(self, user_id: uuid.UUID, lab_id: uuid.UUID, request: ActivateConnectionRequest) -> LabResponse:
        """Activate a connection for the lab"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()

        if not lab:
            raise NotFoundError("Lab not found")

        # Check if user can manage lab
        if not await self._user_can_manage_lab(user_id, lab_id):
            raise AuthorizationError("Insufficient permissions")

        # Check if connection exists and belongs to this lab
        connection = self.db.query(Neo4jConnection).filter(
            and_(Neo4jConnection.id == request.connection_id, Neo4jConnection.lab_id == lab_id)
        ).first()

        if not connection:
            raise NotFoundError("Connection not found or doesn't belong to this lab")

        # Activate connection
        lab.active_connection_id = request.connection_id
        lab.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(lab)

        return LabResponse.from_orm(lab)

    async def _user_has_lab_access(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user has access to lab (owner or member)"""
        lab = self.db.query(Lab).filter(Lab.id == lab_id).first()
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

    async def _user_can_manage_lab(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user can manage lab (owner or admin member)"""
        lab = self.db.query(Lab).filter(Lab.id == lab_id).first()
        if not lab:
            return False

        # Check if owner
        if lab.owner_id == user_id:
            return True

        # Check if admin member
        member = self.db.query(LabMember).filter(
            and_(
                LabMember.lab_id == lab_id,
                LabMember.user_id == user_id,
                LabMember.role == 'admin'
            )
        ).first()
        
        return member is not None
