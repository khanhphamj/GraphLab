from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid
from app.schemas.lab import LabResponse

class PaperBase(BaseModel):
    id: int
    title: str
    abstract: str
    paper_published_at: datetime
    paper_updated_at: datetime
    entry_id: str
    pdf_url: str
    primary_category: str
    categories: Optional[str] = None
    doi: Optional[str] = None
    comment: Optional[str] = None
    journalRef: Optional[str] = None
    license: Optional[str] = None
    lab_id: int

class PaperCreate(PaperBase):
    pass

class PaperUpdate(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    paper_published_at: Optional[datetime] = None
    paper_updated_at: Optional[datetime] = None
    entry_id: Optional[str] = None
    pdf_url: Optional[str] = None
    primary_category: Optional[str] = None
    categories: Optional[str] = None
    doi: Optional[str] = None
    comment: Optional[str] = None
    journalRef: Optional[str] = None
    license: Optional[str] = None

class PaperResponse(PaperBase):
    model_config = ConfigDict(from_attributes=True)

class PaperWithLab(PaperResponse):
    lab: LabResponse
    model_config = ConfigDict(from_attributes=True)