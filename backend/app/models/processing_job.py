import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, ForeignKey, DateTime, JSON, Integer, Enum, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        Index("ix_processing_jobs_lab_id", "lab_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(Enum('paper_crawl', 'paper_process', 'entity_extract', 'vector_embed', 'kg_upsert', 'schema_migrate', 'index_rebuild', 'data_export', 'database_create', name='processing_job_type'), nullable=False)
    status: Mapped[str] = mapped_column(Enum('queued', 'running', 'completed', 'failed', 'cancelled', name='processing_job_status'), nullable=False, default='queued')
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    queue: Mapped[Optional[str]] = mapped_column(String)
    worker_id: Mapped[Optional[str]] = mapped_column(String)
    input_config: Mapped[Optional[dict]] = mapped_column(JSON)
    output_result: Mapped[Optional[dict]] = mapped_column(JSON)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON)
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_items: Mapped[Optional[int]] = mapped_column(Integer)
    retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # relationships
    lab: Mapped["Lab"] = relationship("Lab", back_populates="processing_jobs")
    job_steps: Mapped[list["JobStep"]] = relationship("JobStep", back_populates="job", cascade="all, delete-orphan")
