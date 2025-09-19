from __future__ import annotations

import uuid
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from app.schemas.research_keyword import ResearchKeywordResponse


class KeywordSuggestion(BaseModel):
    """Suggestion returned by the LLM provider before persistence."""

    term: str = Field(..., min_length=1, max_length=255)
    rationale: Optional[str] = Field(
        default=None, max_length=1000, description="Reasoning provided by the agent"
    )
    weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Preliminary importance score suggested by the agent",
    )


class GeneratedKeywordResult(BaseModel):
    """Result of attempting to persist a generated keyword."""

    term: str
    rationale: Optional[str] = None
    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Literal["created", "updated", "skipped", "error"]
    keyword: Optional[ResearchKeywordResponse] = None
    error: Optional[str] = None


class KeywordGenerationResponse(BaseModel):
    """Response returned by the keyword generation endpoint."""

    session_id: uuid.UUID
    suggestions: List[GeneratedKeywordResult]

