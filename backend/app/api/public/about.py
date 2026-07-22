"""GET /api/about — 关于页内容（来自 site_settings 单行表）。"""
from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DBSession
from app.models.settings import SiteSettings
from app.schemas.common import envelope

router = APIRouter()


@router.get("/about")
async def about(db: DBSession) -> dict:
    """关于页：站点名称、作者、版本、扩展字段。"""
    stmt = select(SiteSettings).where(SiteSettings.id == 1)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    if not s:
        return envelope({
            "siteName": "",
            "author": "",
            "version": "",
            "extra": {},
        })
    return envelope({
        "siteName": s.site_name,
        "author": s.author,
        "version": s.version,
        "extra": s.extra or {},
    })
