"""Persona 人设模型。"""
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Persona(Base, UUIDPkMixin, TimestampMixin):
    """AI 对话人设：系统提示词、标签、口吻。"""

    __tablename__ = "personas"

    serial: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    tagline: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    avatar: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="global", nullable=False)

    channels = relationship("Channel", back_populates="persona")
