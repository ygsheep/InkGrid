"""文章模型（posts 表）。"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Post(Base, TimestampMixin):
    """博客文章（即知识库源文档）。

    - slug: URL 友好标识，唯一
    - content_md: Markdown 源码（前端直接渲染，content_html 暂不填充）
    - tags: 标签数组，用于筛选与聚类
    - status: draft | published | archived
    - toc: [{id,title,level}]，由标题层级自动生成
    - channel: 关联频道（删除频道时 RESTRICT 阻止，需先迁移文章）
    """

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reading_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    toc: Mapped[list | None] = mapped_column(
        JSONB, server_default="[]", nullable=True
    )

    # 关系
    channel: Mapped["Channel"] = relationship(  # noqa: F821
        back_populates="posts",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_posts_status_published_at", "status", "published_at"),
        Index("ix_posts_channel_published_at", "channel_id", "published_at"),
    )
