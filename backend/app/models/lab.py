import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = (
        Index("ix_labs_owner_id", "owner_id"),
        Index("ix_labs_active_connection_id", "active_connection_id"),
        Index("ix_labs_active_schema_id", "active_schema_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    research_domain: Mapped[Optional[str]] = mapped_column(String)
    settings: Mapped[Optional[dict]] = mapped_column(JSON)
    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    active_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("neo4j_connections.id"))
    active_schema_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("kg_schemas.id"))
    status: Mapped[str] = mapped_column(Enum('active', 'archived', 'suspended', name='lab_status'), nullable=False, default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc, onupdate=timezone.utc)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # relationships
    owner: Mapped["User"] = relationship("User", back_populates="labs", passive_deletes=True)
    members: Mapped[list["LabMember"]] = relationship("LabMember", back_populates="lab", cascade="all, delete-orphan")
    brainstorm_sessions: Mapped[list["BrainstormSession"]] = relationship("BrainstormSession", back_populates="lab", cascade="all, delete-orphan")
    kg_schemas: Mapped[list["KgSchema"]] = relationship("KgSchema", back_populates="lab", foreign_keys="KgSchema.lab_id", cascade="all, delete-orphan")
    neo4j_connections: Mapped[list["Neo4jConnection"]] = relationship("Neo4jConnection", back_populates="lab", foreign_keys="Neo4jConnection.lab_id", cascade="all, delete-orphan")
    active_connection: Mapped[Optional["Neo4jConnection"]] = relationship("Neo4jConnection", foreign_keys=[active_connection_id], post_update=True)
    active_schema: Mapped[Optional["KgSchema"]] = relationship("KgSchema", foreign_keys=[active_schema_id], post_update=True)
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship("ProcessingJob", back_populates="lab", cascade="all, delete-orphan")
    research_papers: Mapped[list["ResearchPaper"]] = relationship("ResearchPaper", back_populates="lab", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="lab", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="lab", cascade="all, delete-orphan")