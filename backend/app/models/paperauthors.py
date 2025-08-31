from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class PaperAuthor(Base):
    __tablename__ = "paper_authors"
    __table_args__ = (
        UniqueConstraint("paper_id", "author_name", name="uq_paper_authors_paper_author"),
        Index("ix_paper_authors_paper", "paper_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    author_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=False)
    paper: Mapped["Paper"] = relationship("Paper", back_populates="authors")