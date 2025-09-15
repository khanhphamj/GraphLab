"""Research keywords management routes"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models import User
from app.services.research_keyword import ResearchKeywordService
from app.schemas.research_keyword import (
    ResearchKeywordCreate, ResearchKeywordUpdate, ResearchKeywordResponse,
    ResearchKeywordListResponse, BulkKeywordCreate, BulkKeywordDelete,
    BulkOperationResult, SessionKeywordStats
)

router = APIRouter(prefix="/v1", tags=["Research Keywords"])


# Session-scoped routes
@router.post("/brainstorm-sessions/{session_id}/keywords", response_model=ResearchKeywordResponse)
async def create_keyword(
    session_id: uuid.UUID,
    request: ResearchKeywordCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    upsert: bool = Query(False, description="If true, update existing keyword instead of failing")
):
    """Create a new research keyword (Editor+ required)"""
    service = ResearchKeywordService(db)
    keyword, is_created = await service.create_keyword(
        current_user.id, session_id, request, upsert
    )
    
    if is_created:
        return keyword
    else:
        # Return 200 OK for upsert update
        from fastapi import Response
        response = Response(status_code=status.HTTP_200_OK)
        return keyword


@router.post("/brainstorm-sessions/{session_id}/keywords:bulk", response_model=BulkOperationResult)
async def bulk_create_keywords(
    session_id: uuid.UUID,
    request: BulkKeywordCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Bulk create/update keywords (Editor+ required)"""
    service = ResearchKeywordService(db)
    return await service.bulk_create_keywords(current_user.id, session_id, request)


@router.get("/brainstorm-sessions/{session_id}/keywords", response_model=ResearchKeywordListResponse)
async def list_session_keywords(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    source: Optional[str] = Query(None, pattern="^(user|ai|imported)$", description="Filter by source"),
    is_primary: Optional[bool] = Query(None, description="Filter by primary keyword status"),
    q: Optional[str] = Query(None, description="Search query for term or rationale"),
    sort: str = Query("created_at", pattern="^(created_at|term|weight|source)$", description="Sort field"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page")
):
    """List research keywords in session (Viewer+ required)"""
    service = ResearchKeywordService(db)
    return await service.list_session_keywords(
        current_user.id, session_id, source, is_primary, q, sort, order, page, limit
    )


@router.get("/brainstorm-sessions/{session_id}/keywords:stats", response_model=SessionKeywordStats)
async def get_session_keyword_stats(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get keyword statistics for session (Viewer+ required)"""
    service = ResearchKeywordService(db)
    return await service.get_session_keyword_stats(current_user.id, session_id)


@router.post("/brainstorm-sessions/{session_id}/keywords:bulk-delete", response_model=BulkOperationResult)
async def bulk_delete_keywords(
    session_id: uuid.UUID,
    request: BulkKeywordDelete,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Bulk delete keywords (Editor+ required)"""
    service = ResearchKeywordService(db)
    return await service.bulk_delete_keywords(current_user.id, session_id, request)


# Individual keyword routes
@router.get("/research-keywords/{keyword_id}", response_model=ResearchKeywordResponse)
async def get_keyword(
    keyword_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get keyword details (Viewer+ required)"""
    service = ResearchKeywordService(db)
    return await service.get_keyword(current_user.id, keyword_id)


@router.patch("/research-keywords/{keyword_id}", response_model=ResearchKeywordResponse)
async def update_keyword(
    keyword_id: uuid.UUID,
    request: ResearchKeywordUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update keyword (Editor+ required)"""
    service = ResearchKeywordService(db)
    return await service.update_keyword(current_user.id, keyword_id, request)


@router.delete("/research-keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete keyword (Editor+ required)"""
    service = ResearchKeywordService(db)
    await service.delete_keyword(current_user.id, keyword_id)
