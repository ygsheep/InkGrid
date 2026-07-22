"""公开文章路由：GET /api/posts, /api/posts/:slug, /api/channels/:slug/posts。"""
from fastapi import APIRouter, Query

from app.core.errors import NotFoundError
from app.crud.post import post as post_crud
from app.deps import DBSession
from app.schemas.common import Page, envelope
from app.schemas.post import Article, ArticleSummary

router = APIRouter()


def _to_summary(p) -> ArticleSummary:
    """ORM Post → ArticleSummary（与前端字段对齐）。"""
    return ArticleSummary(
        id=str(p.id),
        slug=p.slug,
        title=p.title,
        excerpt=p.excerpt or "",
        channel=p.channel.slug if p.channel else "",
        channelName=p.channel.name if p.channel else "",
        tags=p.tags or [],
        publishedAt=p.published_at.isoformat() if p.published_at else "",
        readingTime=p.reading_time,
    )


def _to_article(p) -> Article:
    """ORM Post → Article（详情）。"""
    base = _to_summary(p)
    return Article(
        **base.model_dump(),
        content=p.content_md,
        html=p.content_html,
        toc=p.toc or [],
    )


@router.get("/posts")
async def list_posts(
    db: DBSession,
    channel: str | None = Query(None, description="频道 slug"),
    tag: str | None = Query(None),
    q: str | None = Query(None, description="title/excerpt 模糊匹配"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """文章列表（仅 published）。"""
    offset = (page - 1) * size
    items, total = await post_crud.list_published(
        db,
        channel=channel,
        tag=tag,
        q=q,
        offset=offset,
        limit=size,
    )
    page_obj = Page[ArticleSummary](
        items=[_to_summary(p) for p in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())


@router.get("/posts/{slug}")
async def get_post(db: DBSession, slug: str) -> dict:
    """文章详情。"""
    p = await post_crud.get_by_slug(db, slug, only_published=True)
    if not p:
        raise NotFoundError("文章不存在")
    return envelope(_to_article(p).model_dump())


@router.get("/channels/{slug}/posts")
async def list_channel_posts(
    db: DBSession,
    slug: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """频道下的文章列表。"""
    offset = (page - 1) * size
    items, total = await post_crud.list_by_channel_slug(
        db, slug, offset=offset, limit=size
    )
    page_obj = Page[ArticleSummary](
        items=[_to_summary(p) for p in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())
