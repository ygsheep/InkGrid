"""真实文章入库端到端验证：PG 文章 → chunk → embed → Milvus → retriever。

用法：
    cd backend; $env:PYTHONPATH="."; py -3.14 poc/smoke_real_article.py
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.milvus import milvus_store
from app.db.session import async_session_factory
from app.ingest.pipeline import ingest_article
from app.models.channel import Channel
from app.models.knowledge import Chunk
from app.models.post import Post

RAG_ARTICLE_MD = """# RAG 检索增强生成详解

## 什么是 RAG

RAG（Retrieval-Augmented Generation，检索增强生成）是一种结合检索和生成的人工智能架构。
它先从知识库检索相关文档片段，再把片段作为上下文输入给大语言模型（LLM）生成回答。
RAG 能有效缓解大模型的幻觉问题，让回答可溯源、可验证。

## RAG 的核心组件

RAG 系统通常包含三个核心组件：

1. **Embedding 模型**：把文本转向量（如 BGE-M3、text-embedding-ada-002）
2. **向量数据库**：存储并检索向量（如 Milvus、Pinecone、Weaviate）
3. **LLM**：基于检索上下文生成回答（如 GPT-4、Qwen、LLaMA）

## RAG 的工作流程

典型流程为：用户提问 → query embedding → 向量库检索 top-k → 重排序 → 组装上下文 → LLM 生成回答。

其中重排序（rerank）是可选但重要的环节，用 cross-encoder 模型对检索结果精排，
能显著提升最终回答质量。常用的 reranker 有 bge-reranker-v2-m3、cohere-reranker 等。

## RAG 的优势

- **减少幻觉**：回答基于检索到的真实文档
- **可溯源**：每个回答可标注引用来源
- **知识可更新**：只需更新知识库，无需重新训练模型
- **领域适配**：接入领域文档即可获得专业问答能力
"""


async def main():
    # 1. 创建/更新测试文章
    async with async_session_factory() as db:
        chan = (
            await db.execute(select(Channel).where(Channel.slug == "blog"))
        ).scalar_one()
        print(f"[1] channel: {chan.slug} ({chan.id})")

        p = (
            await db.execute(select(Post).where(Post.slug == "rag-explained"))
        ).scalar_one_or_none()
        if not p:
            p = Post(
                slug="rag-explained",
                title="RAG 检索增强生成详解",
                content_md=RAG_ARTICLE_MD,
                channel_id=chan.id,
                tags=["rag", "llm", "ai"],
                status="published",
                published_at=datetime.now(timezone.utc),
                reading_time=5,
                toc=[],
            )
            db.add(p)
            await db.flush()
            print(f"[1] created post: {p.id}")
        else:
            p.content_md = RAG_ARTICLE_MD
            p.title = "RAG 检索增强生成详解"
            p.tags = ["rag", "llm", "ai"]
            print(f"[1] updated post: {p.id}")
        await db.commit()
        post_id = p.id

    # 2. 调 ingest_article 入库
    print(f"\n[2] === ingest_article(post_id={post_id}) ===")
    async with async_session_factory() as db:
        doc = await ingest_article(db, post_id)
        await db.commit()
        print(
            f"[2] doc: id={doc.id} status={doc.status} "
            f"chunks={doc.chunk_count} error={doc.error_msg}"
        )

    # 3. 查 PG chunks
    print("\n[3] === PG chunks ===")
    async with async_session_factory() as db:
        chunks = (
            (
                await db.execute(
                    select(Chunk)
                    .where(Chunk.doc_id == doc.id)
                    .order_by(Chunk.seq)
                )
            )
            .scalars()
            .all()
        )
        for c in chunks:
            print(
                f"  seq={c.seq} token_count={c.token_count} "
                f"embedding_id={c.embedding_id!r}"
            )
            print(f"    content: {c.content[:70].replace(chr(10), ' ')}...")
        print(f"[3] total chunks: {len(chunks)}")

    # 4. 查 Milvus
    print("\n[4] === Milvus ===")
    client = milvus_store._get_client()
    stats = client.get_collection_stats("inkgrid_chunks")
    print(f"[4] milvus stats: {stats}")
    partitions = client.list_partitions("inkgrid_chunks")
    print(f"[4] partitions: {partitions}")

    # 5. retriever 检索验证
    print("\n[5] === retriever 检索 ===")
    from app.services.rag.citation import align_citations
    from app.services.rag.reranker import reranker
    from app.services.rag.retriever import retriever

    query = "RAG 有哪些核心组件？"
    hits = await retriever.retrieve(query=query, scope_type="global")
    print(f"[5] query: {query}")
    print(f"[5] retrieved {len(hits)} chunks")
    ranked = await reranker.rerank(query=query, chunks=hits, top_n=3)
    print(f"[5] ranked {len(ranked)} chunks:")
    for i, c in enumerate(ranked):
        print(
            f"  [{i}] score={c['score']:.4f} "
            f"heading={c.get('heading', '')!r} "
            f"article_slug={c.get('article_slug', '')!r} "
            f"content_len={len(c.get('content', ''))}"
        )

    # 6. citation 对齐验证
    print("\n[6] === citation 对齐 ===")
    from app.services.rag.agent import rag_agent

    context = __import__("app.services.rag.context_builder", fromlist=["build_context"]).build_context(ranked)
    answer_parts: list[str] = []
    async for token in rag_agent.stream_answer(
        query=query, context=context, scope_type="global", scope_ref="",
    ):
        answer_parts.append(token)
    answer = "".join(answer_parts)
    citations = align_citations(answer, ranked)
    print(f"[6] answer ({len(answer)} chars)")
    print(f"[6] citations ({len(citations)}):")
    for i, c in enumerate(citations):
        print(
            f"  [{i}] title={c.get('title', '')!r} "
            f"slug={c.get('slug', '')!r} "
            f"snippet_len={len(c.get('snippet', ''))}"
        )

    # 7. 清理测试数据（验证 remove_article_chunks 删 Milvus）
    print("\n[7] === cleanup (验证 remove 删 Milvus) ===")
    from app.ingest.pipeline import remove_article_chunks

    async with async_session_factory() as db:
        count = await remove_article_chunks(db, post_id)
        await db.commit()
        print(f"[7] removed {count} docs (PG + Milvus)")
    client2 = milvus_store._get_client()
    client2.flush("inkgrid_chunks")
    remaining = client2.query(
        "inkgrid_chunks",
        filter=f'doc_id == "{doc.id}"',
        output_fields=["id"],
        limit=10,
    )
    print(f"[7] milvus remaining for doc: {len(remaining)} (should be 0)")

    # 删 post
    async with async_session_factory() as db:
        p = (
            await db.execute(select(Post).where(Post.slug == "rag-explained"))
        ).scalar_one_or_none()
        if p:
            await db.delete(p)
            await db.commit()
            print("[7] post deleted")

    print("\n[DONE] all tech debts verified")


if __name__ == "__main__":
    asyncio.run(main())
