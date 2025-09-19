"""Research paper management routes"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import get_current_active_user, get_lab_by_id
from app.models import User, Lab
from app.services.research_paper import ResearchPaperService
from app.schemas.research_paper import (
    ResearchPaperCreate, ResearchPaperUpdate, ResearchPaperResponse, ResearchPaperListResponse
)
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError, ValidationError

router = APIRouter(prefix="/v1/labs", tags=["Research Papers"])


@router.post("/{lab_id}/papers", response_model=ResearchPaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    lab_id: uuid.UUID,
    request: ResearchPaperCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new research paper in the lab"""
    try:
        service = ResearchPaperService(db)
        # Override lab_id from URL to ensure consistency
        request.lab_id = lab_id
        return await service.create_research_paper(current_user.id, lab_id, request)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{lab_id}/papers", response_model=ResearchPaperListResponse)
async def get_lab_papers(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search query for title, abstract, arxiv_id, or doi")
):
    """Get research papers for a lab with pagination and search"""
    try:
        service = ResearchPaperService(db)
        return await service.get_papers_by_lab(current_user.id, lab_id, page, limit, q)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{lab_id}/papers/{paper_id}", response_model=ResearchPaperResponse)
async def get_paper(
    lab_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a specific research paper by ID"""
    try:
        service = ResearchPaperService(db)
        return await service.get_paper_by_id(current_user.id, lab_id, paper_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{lab_id}/papers/{paper_id}", response_model=ResearchPaperResponse)
async def update_paper(
    lab_id: uuid.UUID,
    paper_id: uuid.UUID,
    request: ResearchPaperUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update a research paper (management permissions required)"""
    try:
        service = ResearchPaperService(db)
        return await service.update_paper(current_user.id, lab_id, paper_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{lab_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    lab_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a research paper (management permissions required)"""
    try:
        service = ResearchPaperService(db)
        await service.delete_paper(current_user.id, lab_id, paper_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
