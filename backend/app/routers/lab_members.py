"""Lab member management routes"""

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import (
    get_current_active_user, get_lab_by_id, require_lab_member_manager
)
from app.models import User, Lab
from app.services.lab_member import LabMemberService
from app.schemas.lab_member import (
    LabMemberCreate, LabMemberUpdate, LabMemberResponse, LabMemberListResponse
)

router = APIRouter(prefix="/v1/labs", tags=["Lab Members"])


@router.post("/{lab_id}/members", response_model=LabMemberResponse)
async def add_member(
    request: LabMemberCreate,
    lab: Annotated[Lab, Depends(require_lab_member_manager)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Add a new member to the lab (admin with manage_members permission only)"""
    lab_member_service = LabMemberService(db)
    return await lab_member_service.add_member(current_user.id, lab.id, request)


@router.get("/{lab_id}/members", response_model=LabMemberListResponse)
async def get_lab_members(
    lab: Annotated[Lab, Depends(get_lab_by_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get all members of the lab (any member can view)"""
    lab_member_service = LabMemberService(db)
    return await lab_member_service.get_lab_members(current_user.id, lab.id)


@router.get("/{lab_id}/members/{user_id}", response_model=LabMemberResponse)
async def get_member(
    user_id: uuid.UUID,
    lab: Annotated[Lab, Depends(get_lab_by_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get specific member information (any member can view)"""
    lab_member_service = LabMemberService(db)
    return await lab_member_service.get_member(current_user.id, lab.id, user_id)


@router.patch("/{lab_id}/members/{user_id}", response_model=LabMemberResponse)
async def update_member(
    user_id: uuid.UUID,
    request: LabMemberUpdate,
    lab: Annotated[Lab, Depends(require_lab_member_manager)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update member role and permissions (admin with manage_members permission only)"""
    lab_member_service = LabMemberService(db)
    return await lab_member_service.update_member(current_user.id, lab.id, user_id, request)


@router.delete("/{lab_id}/members/{user_id}")
async def remove_member(
    user_id: uuid.UUID,
    lab: Annotated[Lab, Depends(require_lab_member_manager)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Remove member from lab (admin with manage_members permission only)"""
    lab_member_service = LabMemberService(db)
    await lab_member_service.remove_member(current_user.id, lab.id, user_id)
    return {"message": "Member removed successfully"}
