"""测试 services/rag/retriever.py：范围路由 + 合并去重 + retrieve mock。

retriever 单例依赖 embedder + milvus_store，两者在 retrieve() 中被调用。
_resolve_scope / _merge_dedupe 是纯方法可直接测；retrieve 用 mock。
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.rag.retriever import Retriever


# ===== _resolve_scope：范围路由纯方法 =====


def test_resolve_scope_global():
    """global 范围 → 搜全 collection（partition_names=None），无 filter。"""
    r = Retriever()
    partitions, filter_expr = r._resolve_scope("global", "")
    assert partitions is None
    assert filter_expr == ""


def test_resolve_scope_global_with_empty_ref():
    """scope_ref 为空时回退 global。"""
    r = Retriever()
    partitions, filter_expr = r._resolve_scope("global", "")
    assert partitions is None


def test_resolve_scope_channel():
    """channel 范围 → channel_{slug} partition。"""
    r = Retriever()
    partitions, filter_expr = r._resolve_scope("channel", "policy")
    assert partitions == ["channel_policy"]
    assert filter_expr == ""


def test_resolve_scope_article():
    """article 范围 → 搜全 collection + article_slug filter。"""
    r = Retriever()
    partitions, filter_expr = r._resolve_scope("article", "my-post")
    assert partitions is None
    assert "my-post" in filter_expr
    assert "article_slug" in filter_expr


def test_resolve_scope_unknown_type_fallback_global():
    """未知 scope_type 回退 global。"""
    r = Retriever()
    partitions, filter_expr = r._resolve_scope("unknown", "ref")
    assert partitions is None
    assert filter_expr == ""


def test_resolve_scope_channel_empty_ref():
    """channel 但 ref 为空 → 回退 global。"""
    r = Retriever()
    partitions, filter_expr = r._resolve_scope("channel", "")
    assert partitions is None


# ===== _merge_dedupe：合并去重纯方法 =====


def _hit(cid: str, score: float, *, content="内容") -> dict:
    """构造检索命中。"""
    return {"id": cid, "score": score, "content": content}


def test_merge_dedupe_empty():
    """两路都空 → 空列表。"""
    r = Retriever()
    assert r._merge_dedupe([], []) == []


def test_merge_dedupe_only_dense():
    """仅稠密有结果。"""
    r = Retriever()
    dense = [_hit("a", 0.9), _hit("b", 0.7)]
    result = r._merge_dedupe(dense, [])
    assert len(result) == 2
    assert result[0]["id"] == "a"  # score 高的在前


def test_merge_dedupe_only_sparse():
    """仅稀疏有结果。"""
    r = Retriever()
    sparse = [_hit("x", 0.5)]
    result = r._merge_dedupe([], sparse)
    assert len(result) == 1
    assert result[0]["id"] == "x"


def test_merge_dedupe_overlap_keep_higher_score():
    """重叠 id 保留更高 score。"""
    r = Retriever()
    dense = [_hit("a", 0.9), _hit("b", 0.7)]
    sparse = [_hit("a", 0.95), _hit("c", 0.6)]
    result = r._merge_dedupe(dense, sparse)
    # 去重后 3 个：a, b, c
    ids = [c["id"] for c in result]
    assert set(ids) == {"a", "b", "c"}
    # a 保留稀疏的 0.95（更高）
    a_chunk = next(c for c in result if c["id"] == "a")
    assert a_chunk["score"] == 0.95


def test_merge_dedupe_sorted_desc():
    """结果按 score 降序。"""
    r = Retriever()
    dense = [_hit("a", 0.3), _hit("b", 0.9)]
    sparse = [_hit("c", 0.6)]
    result = r._merge_dedupe(dense, sparse)
    scores = [c["score"] for c in result]
    assert scores == sorted(scores, reverse=True)
    assert result[0]["id"] == "b"


# ===== retrieve：mock embedder + milvus_store =====


@pytest.mark.asyncio
async def test_retrieve_calls_embedder_and_milvus():
    """retrieve 调用 embedder.embed_query + milvus 双路搜索。"""
    r = Retriever()
    dense_vec = [0.1] * 1024
    sparse_vec = {"key": 0.5}

    with (
        patch(
            "app.services.rag.retriever.embedder.embed_query",
            new_callable=AsyncMock,
            return_value=(dense_vec, sparse_vec),
        ),
        patch(
            "app.services.rag.retriever.milvus_store.search_dense",
            new_callable=AsyncMock,
            return_value=[_hit("d1", 0.9)],
        ),
        patch(
            "app.services.rag.retriever.milvus_store.search_sparse",
            new_callable=AsyncMock,
            return_value=[_hit("s1", 0.8)],
        ),
    ):
        result = await r.retrieve("测试问题", scope_type="global")

    assert len(result) == 2
    ids = {c["id"] for c in result}
    assert ids == {"d1", "s1"}


@pytest.mark.asyncio
async def test_retrieve_channel_scope_uses_partition():
    """channel 范围检索时传入对应 partition。"""
    r = Retriever()
    dense_vec = [0.1] * 1024
    sparse_vec = {"key": 0.5}

    with (
        patch(
            "app.services.rag.retriever.embedder.embed_query",
            new_callable=AsyncMock,
            return_value=(dense_vec, sparse_vec),
        ),
        patch(
            "app.services.rag.retriever.milvus_store.search_dense",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_dense,
        patch(
            "app.services.rag.retriever.milvus_store.search_sparse",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_sparse,
    ):
        result = await r.retrieve("问题", scope_type="channel", scope_ref="policy")

    assert result == []
    # 验证 dense 搜索传入了 channel partition
    _, kwargs = mock_dense.call_args
    assert "channel_policy" in kwargs["partition_names"]


@pytest.mark.asyncio
async def test_retrieve_empty_results():
    """两路都无结果返回空列表。"""
    r = Retriever()
    dense_vec = [0.1] * 1024
    sparse_vec = {"key": 0.5}

    with (
        patch(
            "app.services.rag.retriever.embedder.embed_query",
            new_callable=AsyncMock,
            return_value=(dense_vec, sparse_vec),
        ),
        patch(
            "app.services.rag.retriever.milvus_store.search_dense",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.retriever.milvus_store.search_sparse",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await r.retrieve("无匹配问题", scope_type="global")

    assert result == []
