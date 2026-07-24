"""SQLAlchemy ORM 基类与公共混入。

所有模型继承 Base，并按需混入 TimestampMixin 获得 created_at / updated_at。
表结构必须与 alembic 迁移（alembic/versions/0001_init.py、0002_post_views.py）保持一致。
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


class UUIDPkMixin:
    """UUID 主键混入。

    提供 id 字段（PG UUID，Python 端默认 uuid4）。
    alembic 0001 迁移未对 admins/posts 的 id 设 server_default，
    因此主键值由 ORM 层在插入时生成（非 DB 端 gen_random_uuid()）。
    新表（note_links/note_templates/qa_pairs）迁移里虽然写了
    server_default=gen_random_uuid()，但 ORM 仍会主动传值，行为一致。
    """

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )


class TimestampMixin:
    """带 created_at / updated_at 的时间戳混入。

    - created_at: 插入时由 DB 的 now() 默认填充
    - updated_at: 插入时由 DB 的 now() 默认填充，更新时由 SQLAlchemy 的 onupdate 刷新
    （alembic 迁移未建触发器，依赖 ORM 层 onupdate；裸 SQL 更新需手动设置 updated_at）
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
    )
