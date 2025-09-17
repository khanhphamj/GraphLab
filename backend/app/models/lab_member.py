import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import ForeignKey, DateTime, Enum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class LabMember(Base):
    __tablename__ = "lab_members"
    __table_args__ = (
        UniqueConstraint("lab_id", "user_id", name="uq_lab_members_lab_user"),
        Index("ix_lab_members_lab_id", "lab_id"),
        Index("ix_lab_members_user_id", "user_id"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(Enum('owner', 'admin', 'editor', 'viewer', name='lab_member_role'), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="lab_memberships")
