"""从问题库取推荐追问。

替代原 fallback.py 的关键词模板方法。
搜问题库（chunk_type=qa）的相近问题，排除已引用的 Q&A。
"""
from app.core.logging import get_logger
from app.services.rag.retriever import retriever

logger = get_logger("rag.followups")

#: 取追问数量
FOLLOWUP_COUNT = 3


async def fetch_followups_from_faq(
    query: str,
    scope_type: str = "global",
    scope_ref: str = "",
    exclude_ids: list[str] | None = None,
) -> list[str]:
    """从问题库搜索相关问题作为推荐追问。

    Args:
        query: 增强后的查询（含 keywords）
        scope_type: 检索范围
        scope_ref: 范围引用
        exclude_ids: 需排除的 chunk id 列表（已引用的 Q&A）

    Returns:
        推荐追问问题列表（最多 FOLLOWUP_COUNT 条）
    """
    exclude_set = set(exclude_ids or [])

    try:
        faq_chunks = await retriever.retrieve_faq(
            query=query,
            scope_type=scope_type,
            scope_ref=scope_ref,
            top_k=10,
        )
    except Exception as e:
        logger.warning("followup_faq_search_failed", error=str(e))
        return []

    # 过滤已引用的，取问题文本
    questions: list[str] = []
    for chunk in faq_chunks:
        if chunk.get("id", "") in exclude_set:
            continue
        content = (chunk.get("content") or "").strip()
        if content and content not in questions:
            questions.append(content)
        if len(questions) >= FOLLOWUP_COUNT:
            break

    logger.info(
        "followups_from_faq",
        query=query[:50],
        candidates=len(faq_chunks),
        selected=len(questions),
    )
    return questions
