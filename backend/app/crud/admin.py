"""Admin 博主账号 CRUD（最小实现，P0 鉴权所需）。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin


async def get_by_username(db: AsyncSession, username: str) -> Admin | None:
    """按用户名取博主账号。"""
    stmt = select(Admin).where(Admin.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get(db: AsyncSession, admin_id: str) -> Admin | None:
    """按 id 取博主账号。"""
    from uuid import UUID

    return await db.get(Admin, UUID(str(admin_id)))
