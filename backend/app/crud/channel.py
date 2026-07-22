"""频道 CRUD。

注意：schema 中 persona_id 是字符串，model 中是 UUID。
create/update 时需要转换。model 已配置 posts / persona lazy=selectin。
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate


class CRUDChannel(CRUDBase[Channel, ChannelCreate, ChannelUpdate]):
    """频道数据访问层。"""

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Channel | None:
        """按 slug 取频道（含 persona 与 posts，由 lazy=selectin 自动加载）。"""
        stmt = select(Channel).where(Channel.slug == slug)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Channel], int]:
        """频道列表（按 created_at asc）。"""
        stmt = (
            select(Channel).order_by(Channel.created_at.asc()).offset(offset).limit(limit)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())
        total = (
            await db.execute(select(func.count()).select_from(Channel))
        ).scalar_one()
        return items, total

    async def create(self, db: AsyncSession, obj_in: ChannelCreate) -> Channel:
        """重写：处理 persona_id str -> UUID。"""
        data = obj_in.model_dump(exclude_unset=True)
        if data.get("persona_id"):
            data["persona_id"] = UUID(str(data["persona_id"]))
        db_obj = Channel(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Channel,
        obj_in: ChannelUpdate | dict,
    ) -> Channel:
        """重写：处理 persona_id str -> UUID（含显式清空 None）。"""
        from pydantic import BaseModel

        if isinstance(obj_in, BaseModel):
            data = obj_in.model_dump(exclude_unset=True)
        else:
            data = dict(obj_in)

        if "persona_id" in data:
            pid = data["persona_id"]
            data["persona_id"] = UUID(str(pid)) if pid else None

        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


channel = CRUDChannel(Channel)
