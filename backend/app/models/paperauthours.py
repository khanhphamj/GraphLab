from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class PaperAuthor(Base):
    __tablename__ = "paper_authors"
    __table_args__ = (
        UniqueConstraint("paperId", "authorName", name="uq_paper_authors_paper_author"),
        Index("ix_paper_authors_paper", "paperId"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    authorName: Mapped[str] = mapped_column(String(1000), nullable=False)
    paperId: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=False)
    paper: Mapped["Paper"] = relationship("Paper", back_populates="authors")