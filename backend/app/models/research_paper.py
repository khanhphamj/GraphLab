import uuid
from typing import Optional
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy import String, Text, ForeignKey, DateTime, Date, Enum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ResearchPaper(Base):
    __tablename__ = "research_papers"
    __table_args__ = (
        UniqueConstraint("lab_id", "arxiv_id", name="uq_research_papers_lab_arxiv"),
        UniqueConstraint("lab_id", "doi", name="uq_research_papers_lab_doi"),
        Index("ix_research_papers_lab_id", "lab_id")
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String)
    doi: Mapped[Optional[str]] = mapped_column(String)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text)
    neo4j_uuid: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    processing_status: Mapped[str] = mapped_column(Enum('pending', 'processing', 'completed', 'failed', name='paper_processing_status'), nullable=False, default='pending')
    keywords_matched: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    published_date: Mapped[Optional[date]] = mapped_column(Date)
    crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="research_papers")
    paper_analysis: Mapped[list["PaperAnalysis"]] = relationship("PaperAnalysis", back_populates="paper", cascade="all, delete-orphan")