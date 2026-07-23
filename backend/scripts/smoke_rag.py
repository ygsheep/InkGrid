"""P1 RAG 端到端冒烟脚本。

验证真实链路：Milvus 连接 → collection 初始化 → TEI embedding → 入库 → 稠密检索 → TEI rerank。

前置条件：
- docker compose up milvus etcd minio tei-embedding tei-reranker
- .env 配置 EMBEDDING_TEI_URL / RERANKER_TEI_URL / MILVUS_*

用法：
    cd backend
    python scripts/smoke_rag.py
"""
import asyncio
import sys

# 确保 app 包可导入
sys.path.insert(0, ".")


async def main() -> None:
    from app.config import get_settings
    from app.core.logging import configure_logging, get_logger
    from app.db.milvus import GLOBAL_PARTITION, milvus_store
    from app.ingest.embedder import embedder
    from app.services.rag.reranker import reranker

    configure_logging(debug=True)
    logger = get_logger("smoke.rag")
    settings = get_settings()

    print("=" * 60)
    print("P1 RAG 端到端冒烟测试")
    print(f"  Milvus: {settings.milvus_host}:{settings.milvus_port}")
    print(f"  TEI Embedding: {settings.embedding_tei_url}")
    print(f"  TEI Reranker: {settings.reranker_tei_url}")
    print("=" * 60)

    # ===== 1. Milvus 连接 + collection 初始化 =====
    print("\n[1/6] 初始化 Milvus collection...")
    await milvus_store.init_collection()
    print("  ✓ collection 就绪")

    # ===== 2. TEI embedding 测试文本 =====
    print("\n[2/6] TEI embedding 测试文本...")
    test_chunks = [
        {
            "content": "FastAPI 是一个现代的 Python Web 框架，基于标准 Python 类型提示构建 API。",
            "heading": "FastAPI 简介",
            "article_slug": "fastapi-intro",
        },
        {
            "content": "PydanticAI 是一个用于构建 LLM 应用的 Agent 框架，与 Pydantic v2 深度集成。",
            "heading": "PydanticAI 概述",
            "article_slug": "pydanticai-overview",
        },
        {
            "content": "Milvus 是一个开源的向量数据库，支持稠密和稀疏向量混合检索。",
            "heading": "Milvus 向量库",
            "article_slug": "milvus-intro",
        },
    ]
    texts = [c["content"] for c in test_chunks]
    dense_vectors, sparse_vectors = await embedder.embed_batch(texts)
    print(f"  ✓ embedding 完成: {len(dense_vectors)} 个向量, dim={len(dense_vectors[0])}")
    print(f"  ✓ 稀疏向量: {len(sparse_vectors)} 个（TEI 模式为空 dict）")

    # ===== 3. 写入 Milvus =====
    print("\n[3/6] 写入 Milvus...")
    doc_id = "smoke_test_doc"
    # 先清理旧的
    try:
        await milvus_store.delete_by_doc(doc_id)
        print("  ✓ 清理旧数据")
    except Exception as e:
        print(f"  - 清理跳过: {e}")

    milvus_chunks = []
    for i, (chunk, dense, sparse) in enumerate(
        zip(test_chunks, dense_vectors, sparse_vectors)
    ):
        milvus_chunks.append({
            "id": f"{doc_id}_{i}",
            "doc_id": doc_id,
            "channel": "tech",
            "article_slug": chunk["article_slug"],
            "heading": chunk["heading"],
            "tags": ["测试", "RAG"],
            "content": chunk["content"],
            "vector_dense": dense,
            "vector_sparse": sparse,
        })
    await milvus_store.insert_chunks(GLOBAL_PARTITION, milvus_chunks)
    print(f"  ✓ 写入 {len(milvus_chunks)} 个 chunk 到 partition [{GLOBAL_PARTITION}]")

    # 等待索引刷新
    await asyncio.sleep(1)

    # ===== 4. 稠密检索 =====
    print("\n[4/6] 稠密检索...")
    query = "什么是 PydanticAI？"
    query_dense, query_sparse = await embedder.embed_query(query)
    print(f"  ✓ query embedding 完成, dim={len(query_dense)}")

    dense_results = await milvus_store.search_dense(
        query_dense=query_dense,
        partition_names=[GLOBAL_PARTITION],
        top_k=3,
    )
    print(f"  ✓ 检索到 {len(dense_results)} 个结果:")
    for i, r in enumerate(dense_results):
        print(f"    [{i + 1}] score={r['score']:.4f} | {r['heading']} | {r['content'][:40]}...")

    # ===== 5. TEI rerank =====
    print("\n[5/6] TEI rerank 精排...")
    ranked = await reranker.rerank(query, dense_results, top_n=3)
    print(f"  ✓ rerank 完成, top {len(ranked)}:")
    for i, r in enumerate(ranked):
        print(f"    [{i + 1}] score={r['score']:.4f} | {r['heading']} | {r['content'][:40]}...")

    # ===== 6. 清理 =====
    print("\n[6/6] 清理测试数据...")
    await milvus_store.delete_by_doc(doc_id)
    print("  ✓ 清理完成")

    print("\n" + "=" * 60)
    print("✓ 端到端冒烟测试通过")
    print("  - Milvus 连接 + collection + partition: OK")
    print("  - TEI embedding (BGE-M3): OK")
    print("  - Milvus insert + search: OK")
    print("  - TEI rerank (bge-reranker-v2-m3): OK")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
