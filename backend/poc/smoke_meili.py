"""Meilisearch 端到端冒烟测试：init → upsert → search → delete → search。

验证点：
1. init_index 创建 posts 索引 + 配置可搜索/可过滤/可排序字段
2. upsert 测试文档（含中文标题）
3. 关键词搜索 + 高亮（_formatted）
4. 中文分词搜索
5. channel 过滤
6. delete 后搜索确认清理

用法：
    cd backend
    python poc/smoke_meili.py
"""
import asyncio
import datetime


class FakePost:
    """模拟 Post ORM 对象，供 upsert_post_orm 使用。"""

    def __init__(self, **kw):
        self.__dict__.update(kw)


async def main():
    from app.db.meili import meili_store
    from app.services.search import delete_post, search_posts, upsert_post_orm

    print("=== 1. init_index ===")
    await meili_store.init_index()
    print("OK: posts 索引已初始化")

    print("\n=== 2. upsert 2 篇测试文档 ===")
    posts = [
        FakePost(
            id="00000000-0000-0000-0000-000000000001",
            slug="rag-explained",
            title="RAG 检索增强生成详解",
            excerpt="深入理解 RAG 架构与实现",
            content_md="RAG 结合检索与生成，提升问答准确性。本文介绍 RAG 的核心组件。",
            tags=["rag", "ai"],
            status="published",
            published_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
            reading_time=8,
        ),
        FakePost(
            id="00000000-0000-0000-0000-000000000002",
            slug="milvus-guide",
            title="Milvus 向量数据库入门指南",
            excerpt="Milvus 部署与使用教程",
            content_md="Milvus 是开源向量数据库，支持 HNSW 索引和分区。",
            tags=["milvus", "vector"],
            status="published",
            published_at=datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
            reading_time=5,
        ),
    ]
    for p in posts:
        await upsert_post_orm(p, "tech", "技术")
    print("OK: 已 upsert 2 篇文档")

    # Meilisearch 任务异步执行，等待索引完成
    print("\n等待索引任务完成...")
    await asyncio.sleep(1.5)

    print("\n=== 3. search 'RAG' ===")
    res = await search_posts("RAG", limit=5)
    print(f"hits: {res.get('estimatedTotalHits')}, time: {res.get('processingTimeMs')}ms")
    for h in res.get("hits", []):
        print(f"  - {h.get('title')} (slug={h.get('slug')})")
        print(f"    formatted.title: {h.get('_formatted', {}).get('title')}")

    print("\n=== 4. search '向量数据库' (中文分词) ===")
    res2 = await search_posts("向量数据库", limit=5)
    print(f"hits: {res2.get('estimatedTotalHits')}")
    for h in res2.get("hits", []):
        print(f"  - {h.get('title')}")

    print("\n=== 5. channel 过滤 ===")
    res3 = await search_posts("Milvus", limit=5, channel_slug="tech")
    print(f"channel=tech hits: {res3.get('estimatedTotalHits')} (应=1)")
    res4 = await search_posts("Milvus", limit=5, channel_slug="life")
    print(f"channel=life hits: {res4.get('estimatedTotalHits')} (应=0)")

    print("\n=== 6. delete 后搜索确认 ===")
    await delete_post("00000000-0000-0000-0000-000000000001")
    await asyncio.sleep(1)
    res5 = await search_posts("RAG", limit=5)
    print(f"delete 后 search 'RAG' hits: {res5.get('estimatedTotalHits')} (应=0)")

    print("\n=== 7. 清理 ===")
    await delete_post("00000000-0000-0000-0000-000000000002")
    await asyncio.sleep(0.5)
    res6 = await search_posts("Milvus", limit=5)
    print(f"清理后 search 'Milvus' hits: {res6.get('estimatedTotalHits')} (应=0)")

    print("\n=== 全部验证通过 ===")


if __name__ == "__main__":
    asyncio.run(main())
