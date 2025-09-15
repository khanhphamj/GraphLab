from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid


class ResearchKeywordCreate(BaseModel):
    term: str = Field(..., min_length=1, max_length=255, description="Research keyword term")
    weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Keyword importance weight (0.0-1.0)")
    source: str = Field(default="user", pattern="^(user|ai|imported)$", description="Source of the keyword")
    rationale: Optional[str] = Field(None, max_length=1000, description="Rationale for including this keyword")
    is_primary: bool = Field(default=False, description="Whether this is a primary keyword")

    @validator('term')
    def normalize_term(cls, v):
        """Normalize term: strip whitespace and convert to lowercase for uniqueness"""
        return v.strip().lower() if v else v


class ResearchKeywordUpdate(BaseModel):
    term: Optional[str] = Field(None, min_length=1, max_length=255)
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: Optional[str] = Field(None, pattern="^(user|ai|imported)$")
    rationale: Optional[str] = Field(None, max_length=1000)
    is_primary: Optional[bool] = None

    @validator('term')
    def normalize_term(cls, v):
        """Normalize term: strip whitespace and convert to lowercase for uniqueness"""
        return v.strip().lower() if v else v


class ResearchKeywordResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    term: str
    weight: Optional[float]
    source: str
    rationale: Optional[str]
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ResearchKeywordListResponse(BaseModel):
    items: List[ResearchKeywordResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# Bulk operations schemas
class BulkKeywordItem(BaseModel):
    term: str = Field(..., min_length=1, max_length=255)
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: str = Field(default="user", pattern="^(user|ai|imported)$")
    rationale: Optional[str] = Field(None, max_length=1000)
    is_primary: bool = Field(default=False)

    @validator('term')
    def normalize_term(cls, v):
        return v.strip().lower() if v else v


class BulkKeywordCreate(BaseModel):
    mode: str = Field(default="upsert", pattern="^(upsert|skip|merge)$", description="How to handle duplicates")
    items: List[BulkKeywordItem] = Field(..., min_items=1, max_items=1000, description="Keywords to create")


class BulkKeywordDelete(BaseModel):
    ids: List[uuid.UUID] = Field(..., min_items=1, max_items=1000, description="Keyword IDs to delete")


class BulkOperationResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    deleted: int = 0
    not_found: int = 0
    duplicates: List[str] = Field(default_factory=list, description="Terms that were duplicates")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Processing errors")


# Statistics and aggregation schemas
class KeywordSourceStats(BaseModel):
    user: int = 0
    ai: int = 0
    imported: int = 0


class SessionKeywordStats(BaseModel):
    total_keywords: int
    primary_keywords: int
    by_source: KeywordSourceStats
    avg_weight: Optional[float] = None
    weight_distribution: Dict[str, int] = Field(default_factory=dict)  # e.g., {"0.0-0.2": 5, "0.2-0.4": 10}
