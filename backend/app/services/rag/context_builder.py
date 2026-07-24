"""检索结果 → LLM prompt 上下文组装。

支持两种 chunk 类型：
- article_chunk: 常规文章片段，标注 [n]
- qa: 预生成 Q&A，答案直接作为上下文
"""

# FAQ 短路阈值：FAQ rerank 分数高于此值时，直接用 FAQ 答案作为主上下文
FAQ_SHORT_CIRCUIT_THRESHOLD = 0.8


def build_context(ranked_chunks: list[dict]) -> str:
    """把 rerank 后的 chunks 组装为 LLM 上下文文本。

    格式：
    [1] {heading or article_slug}
    {content}

    [2] {heading or article_slug}
    {content}
    ...

    对于 chunk_type=qa 的片段，额外标注答案：
    [n] 问题：{content}
    参考答案：{answer}

    每个片段用 [n] 标注（n 从 1 开始），与 citation 对齐规则一致。
    chunk 之间用空行分隔。
    """
    blocks: list[str] = []
    for i, chunk in enumerate(ranked_chunks, start=1):
        title = chunk.get("heading") or chunk.get("article_slug") or ""
        content = chunk.get("content") or ""
        chunk_type = chunk.get("chunk_type", "article_chunk")
        answer = chunk.get("answer") or ""

        if chunk_type == "qa" and answer:
            # Q&A 类型：标注问题和答案
            blocks.append(f"[{i}] {title}\n问题：{content}\n参考答案：{answer}")
        else:
            # 文章片段：保持原有格式
            blocks.append(f"[{i}] {title}\n{content}")

    return "\n\n".join(blocks)


def check_faq_short_circuit(ranked_chunks: list[dict]) -> dict | None:
    """检查是否有 FAQ chunk 满足短路条件。

    如果 top-1 是 Q&A 且 rerank 分数 >= 阈值，返回该 chunk（短路）。
    否则返回 None。

    Returns:
        短路的 FAQ chunk dict 或 None
    """
    if not ranked_chunks:
        return None

    top = ranked_chunks[0]
    if top.get("chunk_type") == "qa" and top.get("answer"):
        score = top.get("score", 0.0)
        if score >= FAQ_SHORT_CIRCUIT_THRESHOLD:
            return top

    return None
