from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        UniqueConstraint("labId", "id", name="uq_papers_lab_arxiv"),
        Index("ix_papers_lab", "labId"),
        Index("ix_papers_published_at", "paperPublishedAt"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=False)
    paperPublishedAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=False)
    paperUpdatedAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=False)
    entryId: Mapped[Optional[str]] = mapped_column(String(1000), nullable=False)
    pdfUrl: Mapped[Optional[str]] = mapped_column(String(1000), nullable=False)
    primaryCategory: Mapped[Optional[str]] = mapped_column(String(1000), nullable=False)
    categories: Mapped[Optional[str]] = mapped_column(String(1000))
    doi: Mapped[Optional[str]] = mapped_column(String(1000))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    journalRef: Mapped[Optional[str]] = mapped_column(Text)
    license: Mapped[Optional[str]] = mapped_column(Text)
    
    labId: Mapped[int] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False)

    # relationshipss
    lab: Mapped["Lab"] = relationship("Lab", back_populates="papers")
    authors: Mapped[list["PaperAuthor"]] = relationship("PaperAuthor", back_populates="paper", cascade="all, delete-orphan")