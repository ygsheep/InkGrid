"""Post 文章模型。"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Post(Base, UUIDPkMixin, TimestampMixin):
    """文章：博客主站内容单元，发布即入库。"""

    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_status_published_at", "status", "published_at"),
        Index("ix_posts_channel_published_at", "channel_id", "published_at"),
    )

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(500))
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="RESTRICT"),
        nullable=False,
    )

    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reading_time: Mapped[int | None] = mapped_column(Integer)
    toc: Mapped[list | None] = mapped_column(JSONB, default=list)

    channel = relationship("Channel", back_populates="posts")
