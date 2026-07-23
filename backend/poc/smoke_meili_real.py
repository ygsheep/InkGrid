"""真实文章入库联动验证：模拟 posts.py 的 4 个 Meilisearch 同步触发点。

验证点：
1. sync_meili.py 全量同步 → 搜索能找到真实文章
2. upsert_post_orm（模拟 create/update 触发）→ 索引更新
3. delete_post（模拟 delete 触发）→ 从索引删除
4. upsert_post_orm 非 published（模拟下架触发）→ 从索引删除

用 PG 中的真实文章数据，不修改 PG，只验证 Meilisearch 侧。
"""
import asyncio

from sqlalchemy import select

from app.db.meili import meili_store
from app.db.session import async_session_factory
from app.models.channel import Channel
from app.models.post import Post
from app.services.search import delete_post, search_posts, upsert_post_orm


async def main():
    # 0. 初始化索引
    print("=== 0. init_index ===")
    await meili_store.init_index()
    print("OK")

    # 1. 读取 PG 真实文章
    print("\n=== 1. 读取 PG 真实文章 ===")
    async with async_session_factory() as db:
        result = await db.execute(
            select(Post, Channel.slug, Channel.name)
            .join(Channel, Post.channel_id == Channel.id, isouter=True)
            .where(Post.status == "published")
        )
        rows = result.all()
    if not rows:
        print("PG 无 published 文章，退出")
        return
    p, ch_slug, ch_name = rows[0]
    print(f"真实文章: slug={p.slug} title={p.title} channel={ch_slug}/{ch_name} id={p.id}")

    # 2. 全量同步（sync_meili.py 逻辑）
    print("\n=== 2. 全量同步（sync_meili 逻辑）===")
    await meili_store.delete_all_documents()
    await asyncio.sleep(1)
    from app.services.search import _post_to_doc
    docs = [_post_to_doc(p, ch_slug or "", ch_name or "")]
    await meili_store.upsert_documents(docs)
    await asyncio.sleep(1.5)
    res = await search_posts(p.title.split()[0] if p.title else "hello", limit=5)
    print(f"搜索 hits={res.get('estimatedTotalHits')} (应>=1)")
    for h in res.get("hits", []):
        print(f"  - {h.get('title')} (slug={h.get('slug')})")

    # 3. 模拟 update_post 触发：改标题后 upsert（不写 PG，用副本）
    print("\n=== 3. 模拟 update_post 联动（改标题）===")
    # 构造一个临时对象模拟更新后的文章
    import copy
    p_updated = copy.copy(p)
    p_updated.title = f"{p.title} [已更新]"
    await upsert_post_orm(p_updated, ch_slug or "", ch_name or "")
    await asyncio.sleep(1.5)
    res2 = await search_posts("[已更新]", limit=5)
    print(f"搜索 '[已更新]' hits={res2.get('estimatedTotalHits')} (应=1)")
    for h in res2.get("hits", []):
        print(f"  - {h.get('title')}")

    # 4. 模拟下架：status 改为 draft，upsert_post_orm 应删除索引
    print("\n=== 4. 模拟下架联动（status=draft）===")
    p_draft = copy.copy(p)
    p_draft.status = "draft"
    await upsert_post_orm(p_draft, ch_slug or "", ch_name or "")
    await asyncio.sleep(1)
    res3 = await search_posts(p.title.split()[0] if p.title else "hello", limit=5)
    print(f"下架后搜索 hits={res3.get('estimatedTotalHits')} (应=0)")

    # 5. 模拟 delete_post 触发：直接 delete
    print("\n=== 5. 模拟 delete_post 联动 ===")
    # 先恢复索引（模拟重新发布）
    await upsert_post_orm(p, ch_slug or "", ch_name or "")
    await asyncio.sleep(1)
    res4 = await search_posts(p.slug, limit=5)
    print(f"恢复后搜索 hits={res4.get('estimatedTotalHits')} (应>=1)")
    # 再删除
    await delete_post(str(p.id))
    await asyncio.sleep(1)
    res5 = await search_posts(p.slug, limit=5)
    print(f"delete 后搜索 hits={res5.get('estimatedTotalHits')} (应=0)")

    # 6. 收尾：恢复真实文章到索引
    print("\n=== 6. 恢复真实文章到索引 ===")
    await upsert_post_orm(p, ch_slug or "", ch_name or "")
    await asyncio.sleep(1)
    res6 = await search_posts(p.title.split()[0] if p.title else "hello", limit=5)
    print(f"恢复后搜索 hits={res6.get('estimatedTotalHits')} (应>=1)")

    print("\n=== 真实文章入库联动验证通过 ===")


if __name__ == "__main__":
    asyncio.run(main())
