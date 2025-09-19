from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid

from app.models import ResearchPaper, Lab
from app.schemas.research_paper import (
    ResearchPaperCreate, ResearchPaperUpdate, ResearchPaperResponse, ResearchPaperListResponse
)
from app.utils.exceptions import NotFoundError, AuthorizationError, ValidationError
from app.utils.permissions import LabPermissions


class ResearchPaperService:
    def __init__(self, db: Session):
        self.db = db

    async def create_research_paper(self, user_id: uuid.UUID, lab_id: uuid.UUID, request: ResearchPaperCreate) -> ResearchPaperResponse:
        """Create a new research paper"""
       # Check lab exists and user has management permissions
        user_role = await self._get_user_role_in_lab(user_id, lab_id)
        if not LabPermissions.is_management_role(user_role):
            raise AuthorizationError("Insufficient permissions to create research papers")

        # Get lab to verify it exists
        lab = await self._get_lab_or_raise(lab_id)

        # Check for duplicate paper
        existing = self.db.query(ResearchPaper).filter(
            and_(ResearchPaper.lab_id == lab_id, ResearchPaper.arxiv_id == request.arxiv_id, ResearchPaper.doi == request.doi)
        ).first()

        if existing:
            raise ConflictError("Research paper already exists")

        # Create paper
        paper = ResearchPaper(
            lab_id=lab_id,
            arxiv_id=request.arxiv_id,
            doi=request.doi,
            title=request.title,
            authors=request.authors,
            abstract=request.abstract,
            pdf_url=request.pdf_url,
            processing_status=request.processing_status,
            keywords_matched=request.keywords_matched,
            published_date=request.published_date
        )

        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)

        return ResearchPaperResponse.from_orm(paper)
    
    






    # Private helper methods
    async def _get_lab_or_raise(self, lab_id: uuid.UUID) -> Lab:
        """Get lab or raise NotFoundError"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()
        if not lab:
            raise NotFoundError("Lab not found")
        return lab

    async def _get_user_role_in_lab(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> str:
        """Get user's role in lab"""
        lab = self.db.query(Lab).filter(Lab.id == lab_id).first()
        if not lab:
            raise NotFoundError("Lab not found")
        
        # Check if owner
        if lab.owner_id == user_id:
            return "owner"

        # Check member role
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id, LabMember.left_at.is_(None))
        ).first()
        
        if member:
            return member.role
        
        raise AuthorizationError("User is not a member of this lab")

    