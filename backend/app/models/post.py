"""Post 文章/笔记模型。

文章即知识库：posts 表统一承载博客文章与私有笔记。
- category 标识 7 层目录（inbox/daily/reading/knowledge/projects/templates/assets）
- folder_path 在 knowledge/projects 下表示子目录树（字符串树）
- status: draft / private / published；published 才进博客，绑定 channel_id
- owner_id 预留多笔者，本期单笔者可空
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Post(Base, UUIDPkMixin, TimestampMixin):
    """文章/笔记：博客主站内容单元 + 知识库笔记，发布即入库。"""

    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_status_published_at", "status", "published_at"),
        Index("ix_posts_channel_published_at", "channel_id", "published_at"),
        Index("ix_posts_owner_category", "owner_id", "category"),
        Index("ix_posts_category_folder", "category", "folder_path"),
    )

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(500))
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)

    # 知识库归属与目录
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )  # 笔者归属，本期单笔者可空，预留多租户
    category: Mapped[str] = mapped_column(
        String(20), default="inbox", nullable=False,
    )  # inbox | daily | reading | knowledge | projects | templates | assets
    folder_path: Mapped[str | None] = mapped_column(String(255))
    # 仅 knowledge/projects 使用，如 "knowledge/大模型"；其余 category 为 null

    is_moc: Mapped[bool] = mapped_column(
        default=False, nullable=False, server_default="false",
    )  # 是否为主题地图节点
    source_url: Mapped[str | None] = mapped_column(String(500))  # 阅读笔记/采集来源

    # 发布相关
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="RESTRICT"),
        nullable=True,
    )  # 可空：未发布的私有笔记无频道
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    # draft | private | published；published 才进博客
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reading_time: Mapped[int | None] = mapped_column(Integer)
    toc: Mapped[list | None] = mapped_column(JSONB, default=list)

    channel = relationship("Channel", back_populates="posts")
