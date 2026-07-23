"""P1 RAG 端到端冒烟测试脚本。

验证完整链路：Milvus → Embedder → Retriever → Reranker → RAGAgent → Pipeline

前置条件：
1. docker-compose.dev.yml 全部服务 healthy
2. LM Studio 在 http://localhost:1234 运行

用法：
    cd backend
    py -3.14 poc/smoke_rag.py
"""
import asyncio
import sys
from pathlib import Path

# 确保项目根在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.milvus import GLOBAL_PARTITION, milvus_store
from app.ingest.embedder import embedder
from app.services.rag.reranker import reranker
from app.services.rag.retriever import retriever

configure_logging(debug=True)
logger = get_logger("smoke.rag")
settings = get_settings()

# 测试数据：3 个 chunk（模拟博客文章片段）
TEST_CHUNKS = [
    {
        "id": "test_doc_1_0",
        "doc_id": "test_doc_1",
        "channel": "tech",
        "article_slug": "rag-explained",
        "heading": "什么是 RAG",
        "tags": ["rag", "llm"],
        "content": (
            "RAG（检索增强生成）是一种结合检索和生成的人工智能架构。"
            "它先从知识库检索相关文档片段，再把片段作为上下文输入给 LLM 生成回答。"
            "RAG 能缓解大模型的幻觉问题，让回答可溯源。"
        ),
    },
    {
        "id": "test_doc_1_1",
        "doc_id": "test_doc_1",
        "channel": "tech",
        "article_slug": "rag-explained",
        "heading": "RAG 的核心组件",
        "tags": ["rag", "architecture"],
        "content": (
            "RAG 系统通常包含三个核心组件："
            "（1）Embedding 模型，把文本转向量；"
            "（2）向量库，存储并检索向量；"
            "（3）LLM，基于检索上下文生成回答。"
            "常见的向量库有 Milvus、Pinecone、Weaviate。"
        ),
    },
    {
        "id": "test_doc_2_0",
        "doc_id": "test_doc_2",
        "channel": "life",
        "article_slug": "my-trip",
        "heading": "我的旅行日记",
        "tags": ["travel"],
        "content": (
            "上周去了云南大理，洱海非常美。"
            "租了电动车环湖一圈，沿途看到白族村落和稻田。"
            "建议秋天去，天气最舒服。"
        ),
    },
]


async def step1_init_milvus() -> None:
    """步骤1：初始化 Milvus collection。"""
    print("\n=== Step 1: init Milvus collection ===")
    await milvus_store.init_collection()
    # 确保 global partition 存在（init_collection 已创建，这里幂等确认）
    await milvus_store.ensure_partition(GLOBAL_PARTITION)
    # 同时创建 channel_tech / channel_life partition
    await milvus_store.ensure_partition("channel_tech")
    await milvus_store.ensure_partition("channel_life")
    print("[OK] collection + partitions ready")


async def step2_insert_chunks() -> None:
    """步骤2：对测试 chunks 做 embedding 并写入 Milvus。"""
    print("\n=== Step 2: embed + insert test chunks ===")

    # 先删除旧的测试数据（幂等）
    for doc_id in ["test_doc_1", "test_doc_2"]:
        try:
            await milvus_store.delete_by_doc(doc_id)
            print(f"  deleted old chunks for {doc_id}")
        except Exception as e:
            print(f"  delete {doc_id} failed (ok): {e}")

    # 批量 embedding
    texts = [c["content"] for c in TEST_CHUNKS]
    dense, sparse = await embedder.embed_batch(texts)
    print(f"  embed done: count={len(dense)}, dim={len(dense[0])}, sparse_nonempty={sum(1 for s in sparse if s)}")

    # 组装写入数据
    chunks_to_insert = []
    for i, chunk in enumerate(TEST_CHUNKS):
        chunks_to_insert.append({
            **chunk,
            "vector_dense": dense[i],
            "vector_sparse": sparse[i],
        })

    # 写入各自 channel partition
    for partition in ["channel_tech", "channel_life"]:
        pchunks = [c for c in chunks_to_insert if c["channel"] == partition.split("_")[1]]
        if pchunks:
            await milvus_store.insert_chunks(partition=partition, chunks=pchunks)
            print(f"  inserted {len(pchunks)} chunks to {partition}")

    print("[OK] chunks inserted")


async def step3_retrieve() -> None:
    """步骤3：验证 retriever 检索。"""
    print("\n=== Step 3: retrieve (global scope) ===")
    query = "什么是 RAG？它有哪些组件？"
    chunks = await retriever.retrieve(query=query, scope_type="global")
    print(f"  query: {query}")
    print(f"  retrieved {len(chunks)} chunks:")
    for i, c in enumerate(chunks):
        print(f"    [{i}] score={c['score']:.4f} doc={c['doc_id']} heading={c['heading']!r}")

    # 验证 channel 范围检索
    print("\n--- retrieve (channel=tech) ---")
    chunks_tech = await retriever.retrieve(query=query, scope_type="channel", scope_ref="tech")
    print(f"  retrieved {len(chunks_tech)} chunks (expected 2)")
    for c in chunks_tech:
        print(f"    score={c['score']:.4f} {c['heading']!r}")

    print("\n--- retrieve (channel=life) ---")
    chunks_life = await retriever.retrieve(query=query, scope_type="channel", scope_ref="life")
    print(f"  retrieved {len(chunks_life)} chunks (expected 0~1)")

    assert len(chunks) >= 2, f"global retrieve 应至少返回 2 条，实际 {len(chunks)}"
    assert len(chunks_tech) == 2, f"tech channel 应返回 2 条，实际 {len(chunks_tech)}"
    print("[OK] retriever works")


async def step4_rerank() -> None:
    """步骤4：验证 reranker 精排。"""
    print("\n=== Step 4: rerank ===")
    query = "什么是 RAG？"
    chunks = await retriever.retrieve(query=query, scope_type="global")
    ranked = await reranker.rerank(query=query, chunks=chunks, top_n=3)
    print(f"  query: {query}")
    print(f"  ranked {len(ranked)} chunks:")
    for i, c in enumerate(ranked):
        print(f"    [{i}] rerank_score={c['score']:.4f} heading={c['heading']!r}")
        print(f"        content: {c['content'][:60]}...")

    assert len(ranked) > 0, "rerank 应返回至少 1 条"
    assert ranked[0]["score"] > 0.3, f"top rerank score 应 > 0.3，实际 {ranked[0]['score']}"
    print("[OK] reranker works")


async def step5_agent() -> None:
    """步骤5：验证 RAGAgent LLM 流式生成。"""
    print("\n=== Step 5: RAGAgent stream ===")
    from app.services.rag.agent import rag_agent
    from app.services.rag.context_builder import build_context

    query = "什么是 RAG？"
    chunks = await retriever.retrieve(query=query, scope_type="global")
    ranked = await reranker.rerank(query=query, chunks=chunks, top_n=3)
    context = build_context(ranked)

    print(f"  query: {query}")
    print(f"  context:\n{context[:300]}...")
    print("  streaming answer:")

    tokens = []
    async for token in rag_agent.stream_answer(
        query=query,
        context=context,
        persona_name="技术助手",
        persona_system_prompt="你是一个专业的技术助手，回答简洁准确。",
        scope_type="global",
    ):
        tokens.append(token)
        print(token, end="", flush=True)
    print()

    answer = "".join(tokens)
    assert len(answer) > 10, f"回答长度应 > 10，实际 {len(answer)}"
    print(f"\n[OK] agent stream done, answer_len={len(answer)}")


async def step6_pipeline() -> None:
    """步骤6：完整 pipeline 端到端。"""
    print("\n=== Step 6: full pipeline (run_rag_pipeline) ===")
    from app.services.rag.pipeline import run_rag_pipeline

    query = "RAG 有哪些核心组件？"
    print(f"  query: {query}")

    frame_types = []
    answer = ""
    citations = []
    followups = []

    async for frame in run_rag_pipeline(
        query=query,
        scope_type="global",
        persona_name="技术助手",
        persona_system_prompt="你是一个专业的技术助手，回答简洁准确。",
    ):
        ftype = frame.get("type")
        frame_types.append(ftype)
        print(f"  [frame] {ftype}")

        if ftype == "token":
            answer += frame.get("content", "")
            print(f"    token: {frame.get('content', '')!r}")
        elif ftype == "citation":
            citations = frame.get("data", [])
            print(f"    citations: {len(citations)} items")
        elif ftype == "followup":
            followups = frame.get("questions", [])
            print(f"    followups: {followups}")

    print(f"\n  answer:\n{answer}")
    print(f"\n  frame sequence: {frame_types}")
    assert "done" in frame_types, "pipeline 应以 done 帧结束"
    print("[OK] full pipeline works")


async def cleanup() -> None:
    """清理测试数据。"""
    print("\n=== Cleanup ===")
    for doc_id in ["test_doc_1", "test_doc_2"]:
        try:
            await milvus_store.delete_by_doc(doc_id)
            print(f"  deleted {doc_id}")
        except Exception as e:
            print(f"  delete {doc_id} failed: {e}")


async def main() -> None:
    print("=" * 60)
    print("P1 RAG Smoke Test")
    print("=" * 60)
    print(f"settings: llm_provider={settings.llm_provider}, llm_model={settings.llm_model}")
    print(f"  embedding_tei_url={settings.embedding_tei_url}")
    print(f"  reranker_tei_url={settings.reranker_tei_url}")
    print(f"  milvus={settings.milvus_host}:{settings.milvus_port}")

    try:
        await step1_init_milvus()
        await step2_insert_chunks()
        await step3_retrieve()
        await step4_rerank()
        await step5_agent()
        await step6_pipeline()
        print("\n" + "=" * 60)
        print("ALL STEPS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n!!! SMOKE FAILED: {e}")
        logger.exception("smoke_failed")
        sys.exit(1)
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
