import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Text, ForeignKey, DateTime, Numeric, Boolean, Enum, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ResearchKeyword(Base):
    __tablename__ = "research_keywords"
    __table_args__ = (
        Index("uq_research_keywords_session_term", "session_id", func.lower("term"), unique=True),
        Index("ix_research_keywords_session_id", "session_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("brainstorm_sessions.id", ondelete="CASCADE"), nullable=False)
    term: Mapped[str] = mapped_column(String, nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Numeric)
    source: Mapped[str] = mapped_column(Enum('user', 'ai', 'imported', name='research_keyword_source'), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc)
    
    # relationships
    session: Mapped["BrainstormSession"] = relationship("BrainstormSession", back_populates="research_keywords")
