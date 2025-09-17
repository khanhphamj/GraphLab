import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, ForeignKey, DateTime, Enum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserOauthAccount(Base):
    __tablename__ = "user_oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_oauth_accounts_provider_user"),
        Index("ix_user_oauth_accounts_user_id", "user_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(Enum('google', 'github', 'microsoft', 'facebook', name='oauth_provider'), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_email: Mapped[Optional[str]] = mapped_column(String)
    access_token_id: Mapped[Optional[str]] = mapped_column(String)
    refresh_token_id: Mapped[Optional[str]] = mapped_column(String)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=timezone.utc, onupdate=timezone.utc)
    
    # relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")
