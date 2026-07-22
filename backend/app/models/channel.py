"""Channel 频道模型。"""
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Channel(Base, UUIDPkMixin, TimestampMixin):
    """频道：内容分组，可配置独立人设与问答入口。"""

    __tablename__ = "channels"

    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    accent: Mapped[str | None] = mapped_column(String(20))  # channel|policy
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
    )

    persona = relationship("Persona", back_populates="channels", lazy="selectin")
    posts = relationship(
        "Post", back_populates="channel", lazy="selectin"
    )
