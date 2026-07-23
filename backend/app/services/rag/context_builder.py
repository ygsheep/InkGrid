"""检索结果 → LLM prompt 上下文组装。"""


def build_context(ranked_chunks: list[dict]) -> str:
    """把 rerank 后的 chunks 组装为 LLM 上下文文本。

    格式：
    [1] {heading or article_slug}
    {content}

    [2] {heading or article_slug}
    {content}
    ...

    每个片段用 [n] 标注（n 从 1 开始），与 citation 对齐规则一致。
    chunk 之间用空行分隔。
    """
    blocks: list[str] = []
    for i, chunk in enumerate(ranked_chunks, start=1):
        title = chunk.get("heading") or chunk.get("article_slug") or ""
        content = chunk.get("content") or ""
        blocks.append(f"[{i}] {title}\n{content}")
    return "\n\n".join(blocks)
