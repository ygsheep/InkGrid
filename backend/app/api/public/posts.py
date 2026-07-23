"""公开文章路由：GET /api/posts, /api/posts/:slug, /api/channels/:slug/posts。"""
from fastapi import APIRouter, Query

from app.core.errors import NotFoundError
from app.crud.post import post as post_crud
from app.deps import DBSession
from app.models.post_view import PostView
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
    """文章详情。同时记录一条访问日志（失败不影响响应）。"""
    p = await post_crud.get_by_slug(db, slug, only_published=True)
    if not p:
        raise NotFoundError("文章不存在")
    # 异步记录访问（不阻塞响应，失败静默）
    try:
        db.add(PostView(post_id=p.id))
        await db.commit()
    except Exception:
        await db.rollback()
    return envelope(_to_article(p).model_dump())


@router.get("/posts/{slug}/adjacent")
async def get_adjacent_posts(db: DBSession, slug: str) -> dict:
    """获取同频道的上一篇/下一篇已发布文章。

    按 published_at 降序排列,返回 prev(较新)和 next(较旧)。
    """
    from sqlalchemy import select
    from app.models.post import Post
    from app.models.channel import Channel
    from sqlalchemy.orm import selectinload

    current = await post_crud.get_by_slug(db, slug, only_published=True)
    if not current:
        raise NotFoundError("文章不存在")

    # 上一篇(更新的文章)
    prev_stmt = (
        select(Post)
        .options(selectinload(Post.channel))
        .join(Channel)
        .where(
            Post.status == "published",
            Post.channel_id == current.channel_id,
            Post.id != current.id,
            Post.published_at > current.published_at if current.published_at else Post.published_at.isnot(None),
        )
        .order_by(Post.published_at.asc())
        .limit(1)
    )
    prev_post = (await db.execute(prev_stmt)).scalar_one_or_none()

    # 下一篇(更老的文章)
    next_stmt = (
        select(Post)
        .options(selectinload(Post.channel))
        .join(Channel)
        .where(
            Post.status == "published",
            Post.channel_id == current.channel_id,
            Post.id != current.id,
            Post.published_at < current.published_at if current.published_at else Post.published_at.is_(None),
        )
        .order_by(Post.published_at.desc())
        .limit(1)
    )
    next_post = (await db.execute(next_stmt)).scalar_one_or_none()

    def _adjacent_summary(p):
        return {
            "slug": p.slug,
            "title": p.title,
            "channel": p.channel.slug if p.channel else "",
            "channelName": p.channel.name if p.channel else "",
            "publishedAt": p.published_at.isoformat() if p.published_at else "",
        }

    return envelope({
        "prev": _adjacent_summary(prev_post) if prev_post else None,
        "next": _adjacent_summary(next_post) if next_post else None,
    })


@router.get("/channels/{slug}/posts")
async def list_channel_posts(
    db: DBSession,
    slug: str,
    tag: str | None = Query(None, description="标签筛选"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """频道下的文章列表(可按标签筛选)。"""
    offset = (page - 1) * size
    items, total = await post_crud.list_by_channel_slug(
        db, slug, tag=tag, offset=offset, limit=size
    )
    page_obj = Page[ArticleSummary](
        items=[_to_summary(p) for p in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())
