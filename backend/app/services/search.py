"""Meilisearch 索引同步与查询。

文章发布/更新/下架时同步索引；对外提供搜索查询。
"""
from app.core.logging import get_logger
from app.db.meili import meili_store
from app.models.post import Post

logger = get_logger("services.search")


def _post_to_doc(p: Post, channel_slug: str = "", channel_name: str = "") -> dict:
    """ORM Post → Meilisearch 文档。published_at 转 unix timestamp 便于排序。"""
    published_ts = int(p.published_at.timestamp()) if p.published_at else 0
    return {
        "id": str(p.id),
        "slug": p.slug,
        "title": p.title,
        "excerpt": p.excerpt or "",
        "content": p.content_md,
        "channel_slug": channel_slug,
        "channel_name": channel_name,
        "tags": p.tags or [],
        "status": p.status,
        "published_at": published_ts,
        "reading_time": p.reading_time or 0,
    }


async def upsert_post_orm(
    p: Post, channel_slug: str = "", channel_name: str = ""
) -> None:
    """同步单篇文章到 Meilisearch。

    仅 published 才索引；非 published 则从索引删除（幂等）。
    """
    if p.status != "published":
        await meili_store.delete_document(str(p.id))
        logger.info("meili_post_unpublished_removed", post_id=str(p.id))
        return
    doc = _post_to_doc(p, channel_slug, channel_name)
    await meili_store.upsert_documents([doc])
    logger.info("meili_post_upserted", post_id=str(p.id), slug=p.slug)


async def delete_post(post_id: str) -> None:
    """从索引删除文章。"""
    await meili_store.delete_document(post_id)


async def search_posts(
    q: str, limit: int = 20, channel_slug: str | None = None
) -> dict:
    """搜索已发布文章，返回 Meilisearch 原始响应。"""
    filter_expr = f'channel_slug = "{channel_slug}"' if channel_slug else None
    return await meili_store.search(q, limit=limit, filter_expr=filter_expr)
