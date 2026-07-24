"""测试 services/rag/pipeline.py：端到端 RAG 管道编排（v2: Query Understanding + FAQ-boosted）。

mock query_understanding / retriever / reranker / rag_agent / followups，验证帧序列：
- 正常流程：token* → citation → followup → done
- 无结果兜底：token(no_result) → followup → done
- clarify 分支：clarify → done
- 异常降级：error → done
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas import ws as ws_constants
from app.services.rag.pipeline import run_rag_pipeline, run_rag_pipeline_simple
from app.services.rag.query_understanding import QueryAnalysis


async def _collect_frames(gen) -> list[dict]:
    """收集 async generator 产出的所有帧。"""
    frames: list[dict] = []
    async for frame in gen:
        frames.append(frame)
    return frames


def _async_gen(tokens: list[str]):
    """构造一个 async generator，逐个 yield token。"""
    async def _gen():
        for t in tokens:
            yield t
    return _gen()


def _chunk(
    cid: str, score: float, *, heading="标题A", content="内容片段",
    chunk_type="article_chunk", answer="",
) -> dict:
    """构造 rerank 后的 chunk。"""
    return {
        "id": cid,
        "heading": heading,
        "article_slug": "post-1",
        "content": content,
        "chunk_type": chunk_type,
        "answer": answer,
        "score": score,
    }


def _mock_analysis(
    route: str = "rag", keywords=None, intent="用户意图", query="问题",
) -> QueryAnalysis:
    """构造 mock QueryAnalysis。"""
    return QueryAnalysis(
        keywords=keywords or ["关键词1"],
        intent=intent,
        route=route,
        enhanced_query=query,
    )


# ===== 正常流程 =====


@pytest.mark.asyncio
async def test_pipeline_normal_flow():
    """正常流程：analyze → retrieve_articles → rerank(高分) → agent 流式 → citation → followup → done。"""
    chunks = [_chunk("c1", 0.3, heading="标题A", content="片段A内容")]
    ranked = [_chunk("c1", 0.9, heading="标题A", content="片段A内容")]

    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(route="rag"),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=chunks,
        ),
        patch(
            "app.services.rag.pipeline.reranker.rerank",
            new_callable=AsyncMock,
            return_value=ranked,
        ),
        patch(
            "app.services.rag.pipeline.rag_agent.stream_answer",
            return_value=_async_gen(["根据", "资料[1]", "，结论是X。"]),
        ),
        patch(
            "app.services.rag.pipeline.fetch_followups_from_faq",
            new_callable=AsyncMock,
            return_value=["追问1", "追问2"],
        ),
    ):
        frames = await _collect_frames(
            run_rag_pipeline("问题", scope_type="global")
        )

    types = [f["type"] for f in frames]
    # 3 个 token 帧 + citation + followup + done
    assert types.count(ws_constants.TOKEN) == 3
    assert ws_constants.CITATION in types
    assert ws_constants.FOLLOWUP in types
    assert types[-1] == ws_constants.DONE

    # citation 帧包含对齐结果
    cite_frame = next(f for f in frames if f["type"] == ws_constants.CITATION)
    assert len(cite_frame["data"]) == 1
    assert cite_frame["data"][0]["title"] == "标题A"


@pytest.mark.asyncio
async def test_pipeline_no_citation_when_no_marker():
    """LLM 输出无 [n] 标注时不发 citation 帧。"""
    chunks = [_chunk("c1", 0.5)]
    ranked = [_chunk("c1", 0.9)]

    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=chunks,
        ),
        patch(
            "app.services.rag.pipeline.reranker.rerank",
            new_callable=AsyncMock,
            return_value=ranked,
        ),
        patch(
            "app.services.rag.pipeline.rag_agent.stream_answer",
            return_value=_async_gen(["没有引用的纯文本回答"]),
        ),
        patch(
            "app.services.rag.pipeline.fetch_followups_from_faq",
            new_callable=AsyncMock,
            return_value=["追问1"],
        ),
    ):
        frames = await _collect_frames(
            run_rag_pipeline("问题", scope_type="global")
        )

    types = [f["type"] for f in frames]
    assert ws_constants.CITATION not in types
    assert ws_constants.FOLLOWUP in types
    assert types[-1] == ws_constants.DONE


# ===== 无结果兜底 =====


@pytest.mark.asyncio
async def test_pipeline_no_results_fallback():
    """检索无结果 → no_result token + followup + done。"""
    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        frames = await _collect_frames(
            run_rag_pipeline("无关问题", scope_type="global")
        )

    types = [f["type"] for f in frames]
    assert types[0] == ws_constants.TOKEN
    assert "没有检索到" in frames[0]["content"] or "没有找到" in frames[0]["content"]
    assert ws_constants.FOLLOWUP in types
    assert types[-1] == ws_constants.DONE
    # 不应有 citation
    assert ws_constants.CITATION not in types


# ===== clarify 分支 =====


@pytest.mark.asyncio
async def test_pipeline_clarify_on_low_score():
    """rerank 低分 → clarify 帧 + done，不调 agent。"""
    chunks = [_chunk("c1", 0.1)]
    ranked = [_chunk("c1", 0.1)]  # score < CLARIFY_THRESHOLD(0.3)

    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=chunks,
        ),
        patch(
            "app.services.rag.pipeline.reranker.rerank",
            new_callable=AsyncMock,
            return_value=ranked,
        ),
        patch(
            "app.services.rag.pipeline.rag_agent.stream_answer",
        ) as mock_agent,
    ):
        frames = await _collect_frames(
            run_rag_pipeline("模糊问题", scope_type="global")
        )

    types = [f["type"] for f in frames]
    assert types[0] == ws_constants.CLARIFY
    assert types[-1] == ws_constants.DONE
    # clarify 帧有 options
    assert "options" in frames[0]
    # agent 不应被调用
    mock_agent.assert_not_called()


# ===== 异常降级 =====


@pytest.mark.asyncio
async def test_pipeline_error_on_retrieve_failure():
    """retrieve_articles 抛异常 → error 帧 + done。"""
    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            side_effect=RuntimeError("milvus down"),
        ),
    ):
        frames = await _collect_frames(
            run_rag_pipeline("问题", scope_type="global")
        )

    types = [f["type"] for f in frames]
    assert ws_constants.ERROR in types
    assert types[-1] == ws_constants.DONE


@pytest.mark.asyncio
async def test_pipeline_error_on_agent_failure():
    """agent 流式抛异常 → error 帧 + done。"""
    chunks = [_chunk("c1", 0.5)]
    ranked = [_chunk("c1", 0.9)]

    async def _raise_gen():
        raise RuntimeError("LLM timeout")
        yield  # noqa: unreachable - make it an async generator

    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=chunks,
        ),
        patch(
            "app.services.rag.pipeline.reranker.rerank",
            new_callable=AsyncMock,
            return_value=ranked,
        ),
        patch(
            "app.services.rag.pipeline.rag_agent.stream_answer",
            return_value=_raise_gen(),
        ),
    ):
        frames = await _collect_frames(
            run_rag_pipeline("问题", scope_type="global")
        )

    types = [f["type"] for f in frames]
    assert ws_constants.ERROR in types
    assert types[-1] == ws_constants.DONE


# ===== run_rag_pipeline_simple 非流式版 =====


@pytest.mark.asyncio
async def test_pipeline_simple_no_results():
    """非流式版无结果返回兜底。"""
    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        answer, citations, followups = await run_rag_pipeline_simple(
            "问题", scope_type="global"
        )

    assert "没有检索到" in answer or "没有找到" in answer
    assert citations == []
    assert len(followups) >= 2


@pytest.mark.asyncio
async def test_pipeline_simple_normal():
    """非流式版正常返回 (answer, citations, followups)。"""
    chunks = [_chunk("c1", 0.5, heading="标题A", content="片段A")]
    ranked = [_chunk("c1", 0.9, heading="标题A", content="片段A")]

    with (
        patch(
            "app.services.rag.pipeline.analyze_query",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_faq",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.rag.pipeline.retriever.retrieve_articles",
            new_callable=AsyncMock,
            return_value=chunks,
        ),
        patch(
            "app.services.rag.pipeline.reranker.rerank",
            new_callable=AsyncMock,
            return_value=ranked,
        ),
        patch(
            "app.services.rag.pipeline.rag_agent.stream_answer",
            return_value=_async_gen(["根据[1]，结论是X。"]),
        ),
        patch(
            "app.services.rag.pipeline.fetch_followups_from_faq",
            new_callable=AsyncMock,
            return_value=["追问1", "追问2"],
        ),
    ):
        answer, citations, followups = await run_rag_pipeline_simple(
            "问题", scope_type="global"
        )

    assert "结论是X" in answer
    assert len(citations) == 1
    assert citations[0]["title"] == "标题A"
    assert len(followups) >= 2
