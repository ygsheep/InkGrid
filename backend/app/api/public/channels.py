"""公开频道路由：GET /api/channels, /api/channels/:slug, /api/channels/:slug/tags。"""
from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.core.errors import NotFoundError
from app.crud.channel import channel as channel_crud
from app.deps import DBSession
from app.models.post import Post
from app.schemas.channel import Channel
from app.schemas.common import Page, envelope

router = APIRouter()


def _to_channel(ch) -> Channel:
    """ORM Channel → Channel schema（与前端对齐）。

    postCount 取 posts 关系长度（lazy=selectin 已加载）。
    persona 取人设 tagline 作为提示（P0 简化）。
    """
    return Channel(
        slug=ch.slug,
        name=ch.name,
        description=ch.description or "",
        accent=ch.accent,
        persona=ch.persona.tagline if ch.persona else None,
        postCount=len(ch.posts) if ch.posts is not None else 0,
    )


@router.get("/channels")
async def list_channels(
    db: DBSession,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> dict:
    """频道列表。"""
    offset = (page - 1) * size
    items, total = await channel_crud.list_all(db, offset=offset, limit=size)
    page_obj = Page[Channel](
        items=[_to_channel(ch) for ch in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())


@router.get("/channels/{slug}")
async def get_channel(db: DBSession, slug: str) -> dict:
    """频道详情（含 persona 摘要）。"""
    ch = await channel_crud.get_by_slug(db, slug)
    if not ch:
        raise NotFoundError("频道不存在")
    return envelope(_to_channel(ch).model_dump())


@router.get("/channels/{slug}/tags")
async def list_channel_tags(db: DBSession, slug: str) -> dict:
    """频道下的标签列表及文章数。

    使用 PostgreSQL unnest 展开 tags 数组,按 tag 分组计数。
    仅统计该频道下已发布文章。
    """
    ch = await channel_crud.get_by_slug(db, slug)
    if not ch:
        raise NotFoundError("频道不存在")

    stmt = (
        select(
            func.unnest(Post.tags).label("tag"),
            func.count().label("count"),
        )
        .where(Post.status == "published", Post.channel_id == ch.id)
        .group_by(text("tag"))
        .order_by(text("count DESC"))
    )
    result = await db.execute(stmt)
    items = [
        {"tag": row.tag, "count": row.count}
        for row in result
        if row.tag
    ]
    return envelope({"items": items, "total": len(items)})
