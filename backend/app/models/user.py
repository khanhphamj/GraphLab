import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    profile: Mapped[Optional[dict]] = mapped_column(JSON)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # relationships
    labs: Mapped[list["Lab"]] = relationship("Lab", back_populates="owner", cascade="all, delete-orphan")
    lab_memberships: Mapped[list["LabMember"]] = relationship("LabMember", back_populates="user", cascade="all, delete-orphan")
    brainstorm_sessions: Mapped[list["BrainstormSession"]] = relationship("BrainstormSession", back_populates="created_by_user", cascade="all, delete-orphan")
    kg_schemas: Mapped[list["KgSchema"]] = relationship("KgSchema", back_populates="created_by_user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender", cascade="all, delete-orphan")
    user_sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    user_verifications: Mapped[list["UserVerification"]] = relationship("UserVerification", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts: Mapped[list["UserOauthAccount"]] = relationship("UserOauthAccount", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")