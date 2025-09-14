"""Lab management routes"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import (
    get_current_active_user, get_lab_by_id, require_lab_admin, require_lab_owner
)
from app.models import User, Lab
from app.services.lab import LabService
from app.schemas.lab import (
    LabCreate, LabUpdate, LabResponse, LabListResponse,
    ActivateSchemaRequest, ActivateConnectionRequest
)

router = APIRouter(prefix="/v1/labs", tags=["Labs"])


@router.post("", response_model=LabResponse)
async def create_lab(
    request: LabCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new lab"""
    lab_service = LabService(db)
    return await lab_service.create_lab(current_user.id, request)


@router.get("", response_model=LabListResponse)
async def get_user_labs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status: Optional[str] = Query(None, pattern="^(active|archived|suspended)$", description="Filter by status"),
    q: Optional[str] = Query(None, description="Search query for name, description, or research domain"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Get labs that current user owns or is a member of"""
    lab_service = LabService(db)
    return await lab_service.get_user_labs(
        user_id=current_user.id,
        status=status,
        q=q,
        page=page,
        limit=limit
    )


@router.get("/{lab_id}", response_model=LabResponse)
async def get_lab(
    lab: Annotated[Lab, Depends(get_lab_by_id)]
):
    """Get lab details (any member can view)"""
    return LabResponse.from_orm(lab)


@router.patch("/{lab_id}", response_model=LabResponse)
async def update_lab(
    request: LabUpdate,
    lab: Annotated[Lab, Depends(require_lab_admin)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update lab information (owner or admin only)"""
    lab_service = LabService(db)
    return await lab_service.update_lab(current_user.id, lab.id, request)


@router.delete("/{lab_id}")
async def delete_lab(
    lab: Annotated[Lab, Depends(require_lab_owner)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Soft delete lab (owner only)"""
    lab_service = LabService(db)
    await lab_service.delete_lab(current_user.id, lab.id)
    return {"message": "Lab deleted successfully"}


@router.post("/{lab_id}/activate-schema", response_model=LabResponse)
async def activate_schema(
    request: ActivateSchemaRequest,
    lab: Annotated[Lab, Depends(require_lab_admin)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Activate a schema for the lab (owner or admin only)"""
    lab_service = LabService(db)
    return await lab_service.activate_schema(current_user.id, lab.id, request)


@router.post("/{lab_id}/activate-connection", response_model=LabResponse)
async def activate_connection(
    request: ActivateConnectionRequest,
    lab: Annotated[Lab, Depends(require_lab_admin)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Activate a connection for the lab (owner or admin only)"""
    lab_service = LabService(db)
    return await lab_service.activate_connection(current_user.id, lab.id, request)
