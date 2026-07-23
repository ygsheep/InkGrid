"""GET /api/search — Meilisearch 即时搜索，返回高亮命中。"""
from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.config import get_settings
from app.deps import DBSession
from app.models.post import Post
from app.models.post_view import PostView
from app.schemas.common import envelope
from app.services.search import search_posts

router = APIRouter()


@router.get("/search")
async def search(
    _: DBSession,
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
    channel: str | None = Query(None, description="频道 slug 过滤"),
) -> dict:
    """即时搜索已发布文章，返回高亮命中。

    响应结构：
    - hits[]: 命中文章，含 _formatted 高亮版本（title/excerpt/content）
    - estimatedTotalHits: 估算总命中数
    - processingTimeMs: Meilisearch 处理耗时
    """
    settings = get_settings()
    if not settings.meili_enabled:
        return envelope({"hits": [], "estimatedTotalHits": 0, "query": q})
    raw = await search_posts(q, limit=limit, channel_slug=channel)
    hits = [
        {
            "id": h.get("id"),
            "slug": h.get("slug"),
            "title": h.get("title"),
            "excerpt": h.get("excerpt"),
            "channelSlug": h.get("channel_slug"),
            "channelName": h.get("channel_name"),
            "tags": h.get("tags", []),
            "publishedAt": h.get("published_at"),
            "readingTime": h.get("reading_time"),
            "_formatted": {
                "title": h.get("_formatted", {}).get("title", h.get("title")),
                "excerpt": h.get("_formatted", {}).get("excerpt", h.get("excerpt")),
                "content": h.get("_formatted", {}).get("content", ""),
            },
        }
        for h in raw.get("hits", [])
    ]
    return envelope(
        {
            "hits": hits,
            "estimatedTotalHits": raw.get("estimatedTotalHits", 0),
            "processingTimeMs": raw.get("processingTimeMs", 0),
            "query": raw.get("query", q),
        }
    )


@router.get("/search/suggestions")
async def search_suggestions(db: DBSession, limit: int = Query(5, ge=1, le=20)) -> dict:
    """搜索建议：返回热门文章标题（按近 30 天访问量排序）。

    供搜索框聚焦时展示，帮助用户发现热门内容。
    """
    stmt = (
        select(Post.slug, Post.title, func.count(PostView.id).label("views"))
        .join(PostView, PostView.post_id == Post.id, isouter=True)
        .where(Post.status == "published")
        .group_by(Post.id)
        .order_by(func.count(PostView.id).desc(), Post.published_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    items = [
        {"slug": r[0], "title": r[1], "views": int(r[2] or 0)}
        for r in rows
    ]
    return envelope({"suggestions": items})

