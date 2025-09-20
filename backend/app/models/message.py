import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Integer, BigInteger, Enum, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_sender_id", "sender_id"),
        Index("ix_messages_parent_message_id", "parent_message_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(Enum('system', 'user', 'assistant', 'tool', name='message_role'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(Enum('text', 'query_result', 'schema_suggestion', 'error', name='message_type'), nullable=False)
    tool_calls: Mapped[Optional[dict]] = mapped_column(JSON)
    neo4j_refs: Mapped[Optional[dict]] = mapped_column(JSON)
    parent_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id"))
    thread_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User", back_populates="messages")
    parent_message: Mapped[Optional["Message"]] = relationship("Message", remote_side=[id], foreign_keys=[parent_message_id], back_populates="child_messages")
    child_messages: Mapped[list["Message"]] = relationship("Message", back_populates="parent_message", foreign_keys=[parent_message_id])