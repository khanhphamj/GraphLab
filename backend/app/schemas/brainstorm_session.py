from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class BrainstormSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    status: str = Field(default="active", pattern="^(active|completed|archived)$")
    session_data: Optional[Dict[str, Any]] = Field(None, description="Session metadata and configuration")


class BrainstormSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")
    session_data: Optional[Dict[str, Any]] = None


class ConversationTurn(BaseModel):
    speaker: str = Field(..., min_length=1, description="Identifier of the speaker (e.g., 'user' or 'agent')")
    content: str = Field(..., min_length=1, description="Content of the conversation turn")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the turn was created",
    )


class ConversationUpdate(ConversationTurn):
    """Payload used to append a new conversation turn to a session."""


class KeywordStats(BaseModel):
    keywords_total: int
    primary_count: int
    by_source: Dict[str, int]  # {"user": 5, "ai": 3, "imported": 2}


class BrainstormSessionResponse(BaseModel):
    id: uuid.UUID
    lab_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    session_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    # Optional expanded data
    creator_name: Optional[str] = None
    creator_email: Optional[str] = None
    stats: Optional[KeywordStats] = None

    class Config:
        from_attributes = True


class BrainstormSessionListResponse(BaseModel):
    items: List[BrainstormSessionResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# Action request schemas
class BrainstormSessionActionRequest(BaseModel):
    """Base class for action requests"""
    pass


class CrawlRequest(BrainstormSessionActionRequest):
    providers: Optional[List[str]] = Field(default=["arxiv"], description="Data providers to crawl")
    categories: Optional[List[str]] = Field(None, description="Research categories to filter")
    primary_only: bool = Field(default=False, description="Use only primary keywords")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results per keyword")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range filter")