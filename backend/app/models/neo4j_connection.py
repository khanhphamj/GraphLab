import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Neo4jConnection(Base):
    __tablename__ = "neo4j_connections"
    __table_args__ = (
        UniqueConstraint("lab_id", "connection_name", name="uq_neo4j_connections_lab_name"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    connection_name: Mapped[str] = mapped_column(String, nullable=False)
    uri: Mapped[str] = mapped_column(String, nullable=False)
    database_name: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    secret_id: Mapped[str] = mapped_column(String, nullable=False)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    schema_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("kg_schemas.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="neo4j_connections", foreign_keys=[lab_id])
    schema: Mapped["KgSchema"] = relationship("KgSchema", back_populates="neo4j_connections", foreign_keys=[schema_id])
