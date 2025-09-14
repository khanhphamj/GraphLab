from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
import uuid

from app.models import Lab, LabMember, User
from app.schemas.lab_member import LabMemberCreate, LabMemberUpdate, LabMemberResponse, LabMemberListResponse
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError


class LabMemberService:
    def __init__(self, db: Session):
        self.db = db

    async def add_member(self, current_user_id: uuid.UUID, lab_id: uuid.UUID, request: LabMemberCreate) -> LabMemberResponse:
        """Add a new member to the lab (admin only)"""
        # Check if lab exists
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()
        
        if not lab:
            raise NotFoundError("Lab not found")

        # Check if current user can manage members
        if not await self._user_can_manage_members(current_user_id, lab_id):
            raise AuthorizationError("Insufficient permissions to manage members")

        # Check if user to be added exists
        user = self.db.query(User).filter(
            and_(User.id == request.user_id, User.deleted_at.is_(None))
        ).first()
        
        if not user:
            raise NotFoundError("User not found")

        # Check if user is already a member
        existing_member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == request.user_id)
        ).first()
        
        if existing_member:
            raise ConflictError("User is already a member of this lab")

        # Prevent adding owner role (only one owner per lab)
        if request.role == 'owner':
            raise AuthorizationError("Cannot add owner role. Transfer ownership instead.")

        # Create new member
        member = LabMember(
            lab_id=lab_id,
            user_id=request.user_id,
            role=request.role
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)

        return await self._member_to_response(member)

    async def get_lab_members(self, current_user_id: uuid.UUID, lab_id: uuid.UUID) -> LabMemberListResponse:
        """Get all members of a lab (any member can view)"""
        # Check if lab exists and user has access
        if not await self._user_has_lab_access(current_user_id, lab_id):
            raise AuthorizationError("Access denied")

        # Get all members with user info
        members = self.db.query(LabMember).options(
            joinedload(LabMember.user)
        ).filter(LabMember.lab_id == lab_id).order_by(LabMember.joined_at).all()

        member_responses = []
        for member in members:
            response = await self._member_to_response(member)
            member_responses.append(response)

        return LabMemberListResponse(
            members=member_responses,
            total=len(member_responses)
        )

    async def get_member(self, current_user_id: uuid.UUID, lab_id: uuid.UUID, user_id: uuid.UUID) -> LabMemberResponse:
        """Get specific member info (any member can view)"""
        # Check if user has access to lab
        if not await self._user_has_lab_access(current_user_id, lab_id):
            raise AuthorizationError("Access denied")

        # Get member
        member = self.db.query(LabMember).options(
            joinedload(LabMember.user)
        ).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id)
        ).first()

        if not member:
            raise NotFoundError("Member not found")

        return await self._member_to_response(member)

    async def update_member(
        self, 
        current_user_id: uuid.UUID, 
        lab_id: uuid.UUID, 
        user_id: uuid.UUID, 
        request: LabMemberUpdate
    ) -> LabMemberResponse:
        """Update member role/permissions (admin only)"""
        # Check if current user can manage members
        if not await self._user_can_manage_members(current_user_id, lab_id):
            raise AuthorizationError("Insufficient permissions to manage members")

        # Get member
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id)
        ).first()

        if not member:
            raise NotFoundError("Member not found")

        # Prevent changing owner role (use transfer ownership instead)
        if member.role == 'owner' or (request.role and request.role == 'owner'):
            raise AuthorizationError("Cannot change owner role. Use transfer ownership instead.")

        # Prevent removing the last admin (if updating role)
        if request.role and request.role not in ['admin', 'owner']:
            admin_count = self.db.query(LabMember).filter(
                and_(LabMember.lab_id == lab_id, LabMember.role.in_(['admin', 'owner']))
            ).count()
            
            if admin_count <= 1 and member.role in ['admin', 'owner']:
                raise ConflictError("Cannot remove the last admin/owner from the lab")

        # Update fields
        if request.role is not None:
            member.role = request.role

        self.db.commit()
        self.db.refresh(member)

        return await self._member_to_response(member)

    async def remove_member(self, current_user_id: uuid.UUID, lab_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Remove member from lab (admin only)"""
        # Check if current user can manage members
        if not await self._user_can_manage_members(current_user_id, lab_id):
            raise AuthorizationError("Insufficient permissions to manage members")

        # Get member
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id)
        ).first()

        if not member:
            raise NotFoundError("Member not found")

        # Prevent removing owner or the last admin
        if member.role == 'owner':
            raise AuthorizationError("Cannot remove lab owner. Transfer ownership first.")
            
        if member.role == 'admin':
            admin_count = self.db.query(LabMember).filter(
                and_(LabMember.lab_id == lab_id, LabMember.role.in_(['admin', 'owner']))
            ).count()
            
            if admin_count <= 1:
                raise ConflictError("Cannot remove the last admin from the lab")

        # Remove member
        self.db.delete(member)
        self.db.commit()

    async def _user_has_lab_access(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user has access to lab (owner or member)"""
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

    async def _user_can_manage_members(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user can manage lab members (owner or admin)"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()
        
        if not lab:
            return False

        # Check if lab owner
        if lab.owner_id == user_id:
            return True

        # Check if admin member
        member = self.db.query(LabMember).filter(
            and_(
                LabMember.lab_id == lab_id,
                LabMember.user_id == user_id,
                LabMember.role.in_(['owner', 'admin'])
            )
        ).first()
        
        return member is not None

    async def _member_to_response(self, member: LabMember) -> LabMemberResponse:
        """Convert LabMember to response with user info"""
        # Load user info if not already loaded
        if not hasattr(member, 'user') or member.user is None:
            user = self.db.query(User).filter(User.id == member.user_id).first()
        else:
            user = member.user

        return LabMemberResponse(
            id=member.id,
            lab_id=member.lab_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            left_at=member.left_at,
            user_name=user.name if user else None,
            user_email=user.email if user else None
        )
