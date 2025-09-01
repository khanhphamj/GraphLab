from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.paper import Paper
from app.schemas.paper import PaperCreate, PaperUpdate, PaperResponse
from app.core.validators import validate_name, validate_description
from typing import Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PaperServiceError(Exception):
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details
        self.timestamp = datetime.now(timezone.utc)
        
class PaperNotFoundError(PaperServiceError):
    def __init__(self, paper_id: int):
        super().__init__(
            f"Paper not found with id: {paper_id}",
            error_code="PAPER_NOT_FOUND",
            details={"paper_id": paper_id}
            )

class PaperAlreadyExistsError(PaperServiceError):
    def __init__(self, paper_id: int):
        super().__init__(
            f"Paper already exists with id: {paper_id}",
            error_code="PAPER_ALREADY_EXISTS",
            details={"paper_id": paper_id})

#Helper functions
def _active_by_lab_id(db: Session, lab_id: int, entry_id: str) -> Optional[Paper]:
    return db.query(Paper).filter(
        Paper.lab_id == lab_id, 
        Paper.entry_id == entry_id, 
        Paper.deleted_at.is_(None)).first()

#Service functions
def create_paper(db: Session, paper_in: PaperCreate) -> PaperResponse:
    try:
        existing_paper = _active_by_lab_id(db, paper_in.lab_id, paper_in.entry_id)
        if existing_paper:
            logger.warning(f"Paper already exists with entry id: {paper_in.entry_id}")
            raise PaperAlreadyExistsError(paper_in.entry_id)
        paper = Paper(
            lab_id=paper_in.lab_id,
            entry_id=paper_in.entry_id,
            title=paper_in.title,
            abstract=paper_in.abstract,
            paper_published_at=paper_in.paper_published_at,
            paper_updated_at=paper_in.paper_updated_at,
            pdf_url=paper_in.pdf_url,
            primary_category=paper_in.primary_category,
            categories=paper_in.categories,
            doi=paper_in.doi,
            comment=paper_in.comment,
            journalRef=paper_in.journalRef,
            license=paper_in.license
            )
        db.add(paper)
        db.commit()
        db.refresh(paper)
        logger.info(f"Paper {paper.id}, entry id {paper.entry_id} created successfully")
        return PaperResponse.model_validate(paper)
    except Exception as e:
        logger.error(f"Error creating paper: {e}")
        db.rollback()
        raise

def get_paper(db: Session, lab_id: int, entry_id: str) -> PaperResponse:
    try:
        paper = _active_by_lab_id(db, lab_id, entry_id)
        if not paper:
            logger.warning(f"Paper {entry_id} not found")
            raise PaperNotFoundError(entry_id)
        return PaperResponse.model_validate(paper)
    except Exception as e:
        logger.error(f"Error getting paper: {e}")
        raise

def get_paper_model(db: Session, lab_id: int, entry_id: str) -> Paper:
    try:
        paper = _active_by_lab_id(db, lab_id, entry_id)
        if not paper:
            logger.warning(f"Paper {entry_id} not found")
            raise PaperNotFoundError(entry_id)
        return paper
    except Exception as e:
        logger.error(f"Error getting paper: {e}")
        raise

def get_papers(db: Session, lab_id: int) -> list[PaperResponse]:
    try:
        papers = db.query(Paper).filter(
            Paper.lab_id == lab_id, 
            Paper.deleted_at.is_(None)
            ).all()
        logger.info(f"Found {len(papers)} papers for lab {lab_id}")
        return [PaperResponse.model_validate(paper) for paper in papers]
    except Exception as e:
        logger.error(f"Error getting papers: {e}")
        raise

def update_paper(db: Session, lab_id: int, entry_id: str, paper_in: PaperUpdate) -> PaperResponse:
    try:
        paper = _active_by_lab_id(db, lab_id, entry_id)
        if not paper:
            logger.warning(f"Paper {entry_id} not found")
            raise PaperNotFoundError(entry_id)
        paper.title = paper_in.title
        paper.abstract = paper_in.abstract
        paper.paper_published_at = paper_in.paper_published_at
        paper.paper_updated_at = paper_in.paper_updated_at
        paper.pdf_url = paper_in.pdf_url
        paper.primary_category = paper_in.primary_category
        paper.categories = paper_in.categories
        paper.doi = paper_in.doi
        paper.comment = paper_in.comment
        paper.journalRef = paper_in.journalRef
        paper.license = paper_in.license
        db.commit()
        db.refresh(paper)
        logger.info(f"Paper {paper.id}, entry id {paper.entry_id} updated successfully")
        return PaperResponse.model_validate(paper)
    except Exception as e:
        logger.error(f"Error updating paper: {e}")
        db.rollback()
        raise

def delete_paper(db: Session, lab_id: int, entry_id: str) -> None:
    try:
        paper = _active_by_lab_id(db, lab_id, entry_id)
        if not paper:
            logger.warning(f"Paper {entry_id} not found")
            raise PaperNotFoundError(entry_id)
        db.delete(paper)
        db.commit()
        logger.info(f"Paper {paper.id}, entry id {paper.entry_id} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting paper: {e}")
        db.rollback()
        raise