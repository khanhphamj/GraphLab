import uuid
from typing import Optional
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uix_owner_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner: Mapped["User"] = relationship("User", back_populates="labs", passive_deletes=True)
    papers: Mapped[list["Paper"]] = relationship("Paper", back_populates="lab", cascade="all, delete-orphan", passive_deletes=True)