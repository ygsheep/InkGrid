"""ChatSession / ChatMessage 会话与消息。"""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class ChatSession(Base, UUIDPkMixin, TimestampMixin):
    """问答会话：匿名或注册访客的一次对话。"""

    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_anon_id", "anon_id"),)

    anon_id: Mapped[str | None] = mapped_column(String(64))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
    )
    scope_type: Mapped[str] = mapped_column(String(20), default="global")
    scope_ref: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(200))


class ChatMessage(Base, UUIDPkMixin, TimestampMixin):
    """会话消息：user / assistant / clarify。"""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list | None] = mapped_column(JSONB)
    follow_ups: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
