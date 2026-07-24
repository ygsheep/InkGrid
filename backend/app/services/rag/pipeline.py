"""RAG 端到端管道编排（v2：Query Understanding + FAQ-boosted）。

设计参考：plan/后端设计方案.md §6.2 / §6.7
流程：
  0. Query Understanding（1 次 LLM 结构化输出）
  1. 路由检索：
     - faq_first → FAQ 检索 → 高分短路？→ 直接用 FAQ answer
     - rag → 文章片段检索
     - channel → 频道范围检索
  2. rerank 精排
  3. 阈值判定（clarify？）
  4. 组装上下文（FAQ + 文章片段合并）
  5. LLM 流式生成（人设模板 + 引用标注）
  6. 引用对齐
  7. followups（从问题库取）

作为 async generator yield WS 帧 dict，WS 层遍历发送。
支持取消：WS 层用 asyncio.Task 包装，stop/打断时 task.cancel()。
"""
from collections.abc import AsyncGenerator

from app.config import get_settings
from app.core.logging import get_logger
from app.schemas import ws as ws_constants
from app.services.rag.agent import rag_agent
from app.services.rag.citation import align_citations
from app.services.rag.context_builder import build_context, check_faq_short_circuit
from app.services.rag.fallback import (
    build_clarify_frame,
    build_followups,
    build_no_result_reply,
    should_clarify,
)
from app.services.rag.followups import fetch_followups_from_faq
from app.services.rag.query_understanding import (
    ROUTE_CHANNEL,
    ROUTE_EXTERNAL,
    ROUTE_FAQ_FIRST,
    ROUTE_RAG,
    analyze_query,
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
    """端到端 RAG 管道（v2），yield WS 帧。

    Yields:
        WS 帧 dict，type 可能是: token / citation / clarify / followup / done / error
    """
    settings = get_settings()

    try:
        # 0. Query Understanding（1 次 LLM 结构化输出）
        analysis = await analyze_query(query)
        enhanced_query = analysis.enhanced_query or query

        logger.info(
            "query_understood",
            query=query[:50],
            route=analysis.route,
            keywords=analysis.keywords,
        )

        # 1. 路由检索
        faq_chunks: list[dict] = []
        article_chunks: list[dict] = []

        # FAQ 检索（faq_first 和 rag 路由都搜 FAQ，短路决策在 rerank 后）
        if analysis.route in (ROUTE_FAQ_FIRST, ROUTE_RAG):
            faq_chunks = await retriever.retrieve_faq(
                query=enhanced_query,
                scope_type=scope_type,
                scope_ref=scope_ref,
            )

        # 文章片段检索
        if analysis.route in (ROUTE_RAG, ROUTE_CHANNEL, ROUTE_EXTERNAL):
            article_chunks = await retriever.retrieve_articles(
                query=enhanced_query,
                scope_type=scope_type,
                scope_ref=scope_ref,
            )
        elif analysis.route == ROUTE_FAQ_FIRST and not faq_chunks:
            # faq_first 但 FAQ 无结果 → 回退到文章检索
            article_chunks = await retriever.retrieve_articles(
                query=enhanced_query,
                scope_type=scope_type,
                scope_ref=scope_ref,
            )

        # 合并所有 chunks
        all_chunks = faq_chunks + article_chunks

        # 2. 无结果兜底
        if not all_chunks:
            logger.info("no_results", query=query[:50], scope=f"{scope_type}:{scope_ref}")
            yield {"type": ws_constants.TOKEN, "content": build_no_result_reply()}
            yield {
                "type": ws_constants.FOLLOWUP,
                "questions": build_followups(query, ""),
            }
            yield {"type": ws_constants.DONE}
            return

        # 3. 精排（FAQ + 文章片段一起 rerank）
        ranked = await reranker.rerank(
            query=enhanced_query,
            chunks=all_chunks,
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

        # 5. FAQ 短路检查
        faq_hit = check_faq_short_circuit(ranked)

        # 6. 组装上下文
        context = build_context(ranked)

        # 7. LLM 流式生成（标注 [n]）
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

        # 8. 引用对齐
        citations = align_citations(answer, ranked)
        if citations:
            yield {"type": ws_constants.CITATION, "data": citations}

        # 9. 推荐追问（从问题库取）
        followups = await fetch_followups_from_faq(
            query=analysis.enhanced_query or query,
            scope_type=scope_type,
            scope_ref=scope_ref,
            exclude_ids=[c["articleId"] for c in citations] if citations else [],
        )
        # 无 FAQ 匹配时回退到模板
        if not followups:
            followups = build_followups(query, answer)
        yield {"type": ws_constants.FOLLOWUP, "questions": followups}

        # 10. 完成
        yield {"type": ws_constants.DONE}

        logger.info(
            "pipeline_done",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            route=analysis.route,
            faq_chunks=len(faq_chunks),
            article_chunks=len(article_chunks),
            ranked=len(ranked),
            citations=len(citations),
            faq_short_circuit=faq_hit is not None,
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

    # Query Understanding
    analysis = await analyze_query(query)
    enhanced_query = analysis.enhanced_query or query

    # 检索
    faq_chunks = await retriever.retrieve_faq(enhanced_query, scope_type, scope_ref)
    article_chunks = await retriever.retrieve_articles(enhanced_query, scope_type, scope_ref)
    all_chunks = faq_chunks + article_chunks

    if not all_chunks:
        return build_no_result_reply(), [], build_followups(query, "")

    ranked = await reranker.rerank(enhanced_query, all_chunks, top_n=settings.reranker_top_n)

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
    followups = await fetch_followups_from_faq(
        query=enhanced_query,
        scope_type=scope_type,
        scope_ref=scope_ref,
        exclude_ids=[c["articleId"] for c in citations] if citations else [],
    )
    if not followups:
        followups = build_followups(query, answer)

    return answer, citations, followups
