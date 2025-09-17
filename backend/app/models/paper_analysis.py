import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, ForeignKey, DateTime, JSON, Numeric, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class PaperAnalysis(Base):
    __tablename__ = "paper_analysis"
    __table_args__ = (
        Index("ix_paper_analysis_paper_id", "paper_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("research_papers.id", ondelete="CASCADE"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(Enum('entity_extraction', 'relation_extraction', 'topic_modeling', 'citation_analysis', name='paper_analysis_type'), nullable=False)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric)
    model_used: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc)
    
    # relationships
    paper: Mapped["ResearchPaper"] = relationship("ResearchPaper", back_populates="paper_analysis")
