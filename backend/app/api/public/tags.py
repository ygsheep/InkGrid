"""公开标签路由:GET /api/tags,GET /api/tags/:tag/posts。"""
from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.deps import DBSession
from app.models.post import Post
from app.schemas.common import Page, envelope
from app.schemas.post import ArticleSummary
from app.crud.post import post as post_crud


router = APIRouter()


@router.get("/tags")
async def list_tags(db: DBSession) -> dict:
    """列出全站所有标签及文章数。

    使用 PostgreSQL unnest 展开 tags 数组,按 tag 分组计数。
    仅统计已发布文章。
    """
    # SELECT tag, COUNT(*) FROM (
    #   SELECT unnest(tags) AS tag FROM posts WHERE status='published'
    # ) t GROUP BY tag ORDER BY count DESC
    stmt = (
        select(
            func.unnest(Post.tags).label("tag"),
            func.count().label("count"),
        )
        .where(Post.status == "published")
        .group_by(text("tag"))
        .order_by(text("count DESC"))
    )
    result = await db.execute(stmt)
    items = [
        {"tag": row.tag, "count": row.count}
        for row in result
        if row.tag  # 过滤 NULL
    ]
    return envelope({"items": items, "total": len(items)})


@router.get("/tags/{tag}/posts")
async def list_posts_by_tag(
    db: DBSession,
    tag: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """按标签列出已发布文章。"""
    offset = (page - 1) * size
    items, total = await post_crud.list_published(
        db, tag=tag, offset=offset, limit=size
    )
    page_obj = Page[ArticleSummary](
        items=[
            ArticleSummary(
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
            for p in items
        ],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())
