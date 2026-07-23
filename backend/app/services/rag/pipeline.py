"""RAG 端到端管道编排。

设计参考：plan/后端设计方案.md §6.2 / §6.7
流程：retrieve → rerank → 阈值判定(clarify?) → agent.stream → citation 对齐 → followups

作为 async generator yield WS 帧 dict，WS 层遍历发送。
支持取消：WS 层用 asyncio.Task 包装，stop/打断时 task.cancel()。
"""
from collections.abc import AsyncGenerator

from app.config import get_settings
from app.core.logging import get_logger
from app.schemas import ws as ws_constants
from app.services.rag.agent import rag_agent
from app.services.rag.citation import align_citations
from app.services.rag.context_builder import build_context
from app.services.rag.fallback import (
    build_clarify_frame,
    build_followups,
    build_no_result_reply,
    should_clarify,
)
from app.services.rag.reranker import reranker
from app.services.rag.retriever import retriever

logger = get_logger("rag.pipeline")


async def run_rag_pipeline(
    query: str,
    scope_type: str = "global",
    scope_ref: str = "",
    persona_name: str = "",
    persona_system_prompt: str = "",
) -> AsyncGenerator[dict, None]:
    """端到端 RAG 管道，yield WS 帧。

    Yields:
        WS 帧 dict，type 可能是: token / citation / clarify / followup / done / error
    """
    settings = get_settings()

    try:
        # 1. 检索（稠密+稀疏混合）
        chunks = await retriever.retrieve(
            query=query,
            scope_type=scope_type,
            scope_ref=scope_ref,
        )

        # 2. 无结果兜底
        if not chunks:
            logger.info("no_results", query=query[:50], scope=f"{scope_type}:{scope_ref}")
            yield {"type": ws_constants.TOKEN, "content": build_no_result_reply()}
            yield {
                "type": ws_constants.FOLLOWUP,
                "questions": build_followups(query, ""),
            }
            yield {"type": ws_constants.DONE}
            return

        # 3. 精排
        ranked = await reranker.rerank(
            query=query,
            chunks=chunks,
            top_n=settings.reranker_top_n,
        )

        # 4. 阈值判定 → 澄清
        top_score = ranked[0].get("score", 0.0) if ranked else 0.0
        if should_clarify(top_score):
            logger.info(
                "clarify_triggered",
                query=query[:50],
                top_score=top_score,
            )
            yield build_clarify_frame(query)
            yield {"type": ws_constants.DONE}
            return

        # 5. 组装上下文
        context = build_context(ranked)

        # 6. LLM 流式生成（标注 [n]）
        answer_parts: list[str] = []
        async for token in rag_agent.stream_answer(
            query=query,
            context=context,
            persona_name=persona_name,
            persona_system_prompt=persona_system_prompt,
            scope_type=scope_type,
            scope_ref=scope_ref,
        ):
            yield {"type": ws_constants.TOKEN, "content": token}
            answer_parts.append(token)

        answer = "".join(answer_parts)

        # 7. 引用对齐
        citations = align_citations(answer, ranked)
        if citations:
            yield {"type": ws_constants.CITATION, "data": citations}

        # 8. 推荐追问
        followups = build_followups(query, answer)
        yield {"type": ws_constants.FOLLOWUP, "questions": followups}

        # 9. 完成
        yield {"type": ws_constants.DONE}

        logger.info(
            "pipeline_done",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            chunks=len(chunks),
            ranked=len(ranked),
            citations=len(citations),
            answer_len=len(answer),
        )

    except Exception as e:
        logger.exception("pipeline_error", query=query[:50], error=str(e))
        yield {
            "type": ws_constants.ERROR,
            "code": ws_constants.ERR_INTERNAL,
            "message": "问答处理失败，请稍后重试",
        }
        yield {"type": ws_constants.DONE}


async def run_rag_pipeline_simple(
    query: str,
    scope_type: str = "global",
    scope_ref: str = "",
) -> tuple[str, list[dict], list[str]]:
    """非流式版 RAG 管道（语音模块 / 测试用）。

    Returns:
        (answer, citations, followups)
    """
    settings = get_settings()

    chunks = await retriever.retrieve(query, scope_type, scope_ref)
    if not chunks:
        return build_no_result_reply(), [], build_followups(query, "")

    ranked = await reranker.rerank(query, chunks, top_n=settings.reranker_top_n)

    top_score = ranked[0].get("score", 0.0) if ranked else 0.0
    # 非流式模式不做 clarify（语音场景直接回答）
    context = build_context(ranked)

    answer_parts: list[str] = []
    async for token in rag_agent.stream_answer(
        query=query,
        context=context,
        scope_type=scope_type,
        scope_ref=scope_ref,
    ):
        answer_parts.append(token)
    answer = "".join(answer_parts)

    citations = align_citations(answer, ranked)
    followups = build_followups(query, answer)

    return answer, citations, followups
