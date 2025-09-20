from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models import User
from app.services.brainstorm_session import BrainstormSessionService
from app.schemas.brainstorm_session import (
    BrainstormSessionCreate, BrainstormSessionUpdate, BrainstormSessionResponse,
    BrainstormSessionListResponse, CrawlRequest, BrainstormSessionActionRequest, CrawlResponse
)

router = APIRouter(prefix="/v1", tags=["Brainstorm Sessions"])


# Lab-scoped routes
@router.post("/labs/{lab_id}/brainstorm-sessions", response_model=BrainstormSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    lab_id: uuid.UUID,
    request: BrainstormSessionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new brainstorm session (Admin required)"""
    service = BrainstormSessionService(db)
    return await service.create_session(current_user.id, lab_id, request)


@router.get("/labs/{lab_id}/brainstorm-sessions", response_model=BrainstormSessionListResponse)
async def list_lab_sessions(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status: Optional[str] = Query(None, pattern="^(active|completed|archived)$", description="Filter by status"),
    q: Optional[str] = Query(None, description="Search query for title or description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", pattern="^(created_at|updated_at|title|status)$", description="Sort field"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """List brainstorm sessions in lab (Viewer+ required)"""
    service = BrainstormSessionService(db)
    return await service.list_lab_sessions(
        current_user.id, lab_id, status, q, page, limit, sort, order
    )


# Session-specific routes
@router.get("/brainstorm-sessions/{session_id}", response_model=BrainstormSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    expand: Optional[str] = Query(None, description="Comma-separated list of fields to expand (stats)")
):
    """Get session details (Viewer+ required)"""
    service = BrainstormSessionService(db)
    expand_stats = expand and "stats" in expand.split(",")
    return await service.get_session(current_user.id, session_id, expand_stats)


@router.patch("/brainstorm-sessions/{session_id}", response_model=BrainstormSessionResponse)
async def update_session(
    session_id: uuid.UUID,
    request: BrainstormSessionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update session (Admin required)"""
    service = BrainstormSessionService(db)
    return await service.update_session(current_user.id, session_id, request)


@router.delete("/brainstorm-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Soft delete session (Admin required)"""
    service = BrainstormSessionService(db)
    await service.delete_session(current_user.id, session_id)


# Action routes
@router.post("/brainstorm-sessions/{session_id}:finalize", response_model=BrainstormSessionResponse)
async def finalize_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Finalize/lock session (Admin required)"""
    service = BrainstormSessionService(db)
    return await service.finalize_session(current_user.id, session_id)


@router.post("/brainstorm-sessions/{session_id}:archive", response_model=BrainstormSessionResponse)
async def archive_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Archive session (Admin required)"""
    service = BrainstormSessionService(db)
    return await service.archive_session(current_user.id, session_id)


@router.post("/brainstorm-sessions/{session_id}:unarchive", response_model=BrainstormSessionResponse)
async def unarchive_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Unarchive session (Admin required)"""
    service = BrainstormSessionService(db)
    return await service.unarchive_session(current_user.id, session_id)


@router.post("/brainstorm-sessions/{session_id}:clone", response_model=BrainstormSessionResponse, status_code=status.HTTP_201_CREATED)
async def clone_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Clone session with keywords (Admin required)"""
    service = BrainstormSessionService(db)
    return await service.clone_session(current_user.id, session_id)


@router.post("/brainstorm-sessions/{session_id}:crawl", response_model=CrawlResponse)
async def kickoff_crawl(
    session_id: uuid.UUID,
    request: CrawlRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Start crawling job from session keywords (Admin with can_run_jobs required)"""
    service = BrainstormSessionService(db)
    return await service.kickoff_crawl(current_user.id, session_id, request)