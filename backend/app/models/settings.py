"""站点设置模型（site_settings 单行表）。"""
from sqlalchemy import JSON, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SiteSettings(Base):
    """站点设置（单行表，id 固定为 1）。

    - site_name / author / version: 站点基本信息
    - extra: 扩展配置（JSONB），如采集源、自定义菜单等
    """

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_name: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
