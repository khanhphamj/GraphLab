from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ResearchPaperCreate(BaseModel):
    lab_id: Optional[uuid.UUID] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    authors: Optional[List[str]] = None
    abstract: str = Field(..., min_length=1, max_length=2000)
    pdf_url: Optional[str] = None
    processing_status: str = "pending"
    keywords_matched: Optional[List[str]] = None
    published_date: Optional[datetime] = None


class ResearchPaperUpdate(BaseModel):
    lab_id: Optional[uuid.UUID] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    authors: Optional[List[str]] = None
    abstract: Optional[str] = Field(None, min_length=1, max_length=2000)
    pdf_url: Optional[str] = None
    processing_status: Optional[str] = Field(None, pattern="^(pending|processing|completed|failed)$")
    keywords_matched: Optional[List[str]] = None
    published_date: Optional[datetime] = None
    crawled_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class ResearchPaperResponse(BaseModel):
    id: uuid.UUID
    lab_id: uuid.UUID
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    title: str
    authors: Optional[List[str]] = None
    abstract: str
    pdf_url: Optional[str] = None
    processing_status: str
    keywords_matched: Optional[List[str]] = None
    published_date: Optional[datetime] = None
    crawled_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResearchPaperListResponse(BaseModel):
    papers: List[ResearchPaperResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool