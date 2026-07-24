"""频道模型（channels 表）。"""
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Channel(Base, TimestampMixin):
    """频道：按知识域组织文章。

    - slug: URL 友好标识，唯一
    - persona_id: 关联人设（删除人设时 SET NULL）
    - accent: channel | policy，前端主题色 / 渲染策略
    - posts: 反向关系（lazy=selectin，便于 list 接口预加载）
    """

    __tablename__ = "channels"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    accent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    persona_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 关系：避免在 list 场景触发 N+1，crud 层用 selectinload 显式加载
    posts: Mapped[list["Post"]] = relationship(  # noqa: F821
        back_populates="channel",
        lazy="selectin",
    )
    persona: Mapped["Persona | None"] = relationship(  # noqa: F821
        lazy="selectin",
    )
