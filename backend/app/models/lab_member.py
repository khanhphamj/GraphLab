import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class LabMember(Base):
    __tablename__ = "lab_members"
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(Enum('admin', 'editor', 'viewer', name='lab_member_role'), nullable=False, default='viewer')
    can_manage_members: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_edit_schema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_run_jobs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_delete_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="lab_memberships")
