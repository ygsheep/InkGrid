"""后台站点设置路由：GET/PATCH /admin/settings。"""
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.deps import AdminId, DBSession
from app.models.settings import SiteSettings
from app.schemas.common import envelope

router = APIRouter(prefix="/settings")


class SettingsUpdate(BaseModel):
    """站点设置更新入参（全字段可选）。"""

    site_name: str | None = None
    author: str | None = None
    version: str | None = None
    extra: dict | None = None


async def _get_or_create(db) -> SiteSettings:
    """读取单行设置；不存在则用默认值创建。"""
    stmt = select(SiteSettings).where(SiteSettings.id == 1)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    if not s:
        s = SiteSettings(
            id=1,
            site_name="InkGrid",
            author="博主",
            version="v1.0.0",
            extra={},
        )
        db.add(s)
        await db.flush()
    return s


def _to_dict(s: SiteSettings) -> dict:
    return {
        "siteName": s.site_name,
        "author": s.author,
        "version": s.version,
        "extra": s.extra or {},
    }


@router.get("")
async def get_settings(db: DBSession, _: AdminId) -> dict:
    """读取站点设置。"""
    s = await _get_or_create(db)
    return envelope(_to_dict(s))


@router.patch("")
async def update_settings(
    db: DBSession,
    _: AdminId,
    payload: SettingsUpdate,
) -> dict:
    """更新站点设置。"""
    s = await _get_or_create(db)
    data = payload.model_dump(exclude_unset=True)
    if "site_name" in data:
        s.site_name = data["site_name"]
    if "author" in data:
        s.author = data["author"]
    if "version" in data:
        s.version = data["version"]
    if "extra" in data:
        s.extra = data["extra"]
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return envelope(_to_dict(s))
