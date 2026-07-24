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

        # 2. 无结果 → 跳过精排，用空 context 走 LLM（LLM 兜底比固定文案体验更好）
        if not chunks:
            logger.info("no_results", query=query[:50], scope=f"{scope_type}:{scope_ref}")
            context = "（无参考资料，请基于自身知识回答）"
            ranked = []
        else:
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
                    threshold=get_settings().rag_clarify_threshold,
                )
                # 发 clarify 帧让前端展示选项卡片
                yield build_clarify_frame(query)
                # 同时把引导文案作为 token 帧发出，让前端消息流有内容、chat.py 能持久化
                clarify_text = build_clarify_frame(query)["content"]
                yield {"type": ws_constants.TOKEN, "content": clarify_text}
                yield {"type": ws_constants.DONE}
                return

            # 5. 组装上下文
            context = build_context(ranked)

        # 6. LLM 流式生成（标注 [n]）
        # reasoning 模型会先输出思考过程（reasoning 帧），再输出正式回答（token 帧）
        answer_parts: list[str] = []
        reasoning_parts: list[str] = []  # 收集思考过程，用于 content 为空时的诊断
        async for kind, delta in rag_agent.stream_answer(
            query=query,
            context=context,
            persona_name=persona_name,
            persona_system_prompt=persona_system_prompt,
            scope_type=scope_type,
            scope_ref=scope_ref,
        ):
            if kind == "reasoning":
                reasoning_parts.append(delta)
                yield {"type": ws_constants.REASONING, "content": delta}
            else:
                yield {"type": ws_constants.TOKEN, "content": delta}
                answer_parts.append(delta)

        answer = "".join(answer_parts)

        # 诊断：思考模型只输出了 reasoning 没有 content（思考占满 max_tokens）
        if not answer and reasoning_parts:
            reasoning_len = sum(len(p) for p in reasoning_parts)
            logger.error(
                "reasoning_exhausted_tokens",
                query=query[:50],
                reasoning_chars=reasoning_len,
                hint="思考过程占满 max_tokens 导致正式回答为空，请增大 llm_max_tokens 或缩短上下文",
            )
            yield {
                "type": ws_constants.ERROR,
                "code": ws_constants.ERR_INTERNAL,
                "message": "模型思考过程过长，未能生成正式回答。请在设置中增大 max_tokens 或换用非思考模型。",
            }
            yield {"type": ws_constants.DONE}
            return

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
        logger.exception(
            "pipeline_error",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            error=str(e),
            error_type=type(e).__name__,
        )
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
    async for kind, delta in rag_agent.stream_answer(
        query=query,
        context=context,
        scope_type=scope_type,
        scope_ref=scope_ref,
    ):
        # 非流式版只收集正式回答，丢弃 reasoning（语音场景无需思考过程）
        if kind == "content":
            answer_parts.append(delta)
    answer = "".join(answer_parts)

    citations = align_citations(answer, ranked)
    followups = build_followups(query, answer)

    return answer, citations, followups
