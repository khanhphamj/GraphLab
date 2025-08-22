from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        UniqueConstraint("lab_id", "arxiv_id", name="uq_papers_lab_arxiv"),
        Index("ix_papers_lab", "lab_id"),
        Index("ix_papers_published_at", "published_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[Optional[str]] = mapped_column(String(500))
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False)
    lab: Mapped["Lab"] = relationship("Lab", back_populates="papers")