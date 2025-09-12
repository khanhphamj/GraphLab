import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    lab_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(Enum('login', 'logout', 'register', 'password_change', 'lab_create', 'lab_delete', 'api_key_create', 'data_export', 'schema_change', name='audit_action'), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String)
    resource_id: Mapped[Optional[str]] = mapped_column(String)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    json_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    lab: Mapped[Optional["Lab"]] = relationship("Lab", back_populates="audit_logs")
