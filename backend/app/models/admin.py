"""Admin 博主账号 + AuditLog 审计日志。"""
import uuid

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Admin(Base, UUIDPkMixin, TimestampMixin):
    """博主账号。"""

    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)


class AuditLog(Base):
    """审计日志：后台写操作 + 公开问答异常。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[str | None] = mapped_column(String(100))
    meta: Mapped[dict | None] = mapped_column(JSONB)
