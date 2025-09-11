import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Boolean, Integer, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class KgSchema(Base):
    __tablename__ = "kg_schemas"
    __table_args__ = (
        UniqueConstraint("lab_id", "version", name="uq_kg_schemas_lab_version"),
        CheckConstraint("version > 0", name="ck_kg_schemas_version_positive"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_definition: Mapped[Optional[dict]] = mapped_column(JSON)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="kg_schemas")
    created_by_user: Mapped["User"] = relationship("User", back_populates="kg_schemas")
    neo4j_connections: Mapped[list["Neo4jConnection"]] = relationship("Neo4jConnection", back_populates="schema", cascade="all, delete-orphan")
