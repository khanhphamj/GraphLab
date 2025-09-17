import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class BrainstormSession(Base):
    __tablename__ = "brainstorm_sessions"
    __table_args__ = (
        Index("ix_brainstorm_sessions_lab_id", "lab_id"),
        Index("ix_brainstorm_sessions_created_by", "created_by"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum('active', 'completed', 'archived', name='brainstorm_session_status'), nullable=False, default='active')
    session_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc, onupdate=timezone.utc)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="brainstorm_sessions")
    created_by_user: Mapped["User"] = relationship("User", back_populates="brainstorm_sessions")
    research_keywords: Mapped[list["ResearchKeyword"]] = relationship("ResearchKeyword", back_populates="session", cascade="all, delete-orphan")
