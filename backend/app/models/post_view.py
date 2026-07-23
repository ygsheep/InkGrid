"""PostView 文章访问日志模型。

每次访问文章详情记录一条，用于看板 monthlyViews 统计。
访问量大时后续可加聚合表或 Redis 计数优化。
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PostView(Base):
    """文章访问记录。"""

    __tablename__ = "post_views"
    __table_args__ = (
        # 按文章 + 时间查询（看板按月统计）
        Index("ix_post_views_post_created", "post_id", "created_at"),
        # 按时间查询（看板本月总量）
        Index("ix_post_views_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
