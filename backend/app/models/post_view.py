"""文章访问日志模型（post_views 表，迁移 0002）。"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PostView(Base):
    """单次文章访问记录，用于看板 monthlyViews 精确统计。

    任何 GET /api/posts/:slug 都会插入一条（失败不阻断响应）。
    """

    __tablename__ = "post_views"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    post_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_post_views_post_created", "post_id", "created_at"),
        Index("ix_post_views_created", "created_at"),
    )
