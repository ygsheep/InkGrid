"""手动同步 Meilisearch 索引：从 PG 全量灌入。

用法：
    cd backend
    python -m scripts.sync_meili
    # 或
    python scripts/sync_meili.py

仅同步 status=published 的文章。先清空索引再全量写入（重建）。
适用于：首次接入、索引损坏重建、批量数据迁移后修正。
"""
import asyncio

from sqlalchemy import select

from app.db.meili import meili_store
from app.db.session import async_session_factory
from app.models.channel import Channel
from app.models.post import Post
from app.services.search import _post_to_doc


async def main() -> None:
    # 1. 初始化索引（幂等）
    await meili_store.init_index()
    # 2. 清空旧数据（避免残留已下架文章）
    await meili_store.delete_all_documents()
    # 3. 从 PG 全量读取 published 文章
    async with async_session_factory() as db:
        result = await db.execute(
            select(Post, Channel.slug, Channel.name)
            .join(Channel, Post.channel_id == Channel.id, isouter=True)
            .where(Post.status == "published")
            .order_by(Post.published_at.desc())
        )
        rows = result.all()
        docs = [
            _post_to_doc(p, ch_slug or "", ch_name or "")
            for p, ch_slug, ch_name in rows
        ]
    if not docs:
        print("no published posts to sync")
        return
    # 4. 批量写入
    await meili_store.upsert_documents(docs)
    print(f"synced {len(docs)} published posts to meilisearch")


if __name__ == "__main__":
    asyncio.run(main())
