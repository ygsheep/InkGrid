"""引用对齐：LLM 输出 [n] 标注与 chunk 映射。"""
import re

#: 匹配 [1] [12] 这类数字标注
_CITATION_RE = re.compile(r"\[(\d+)\]")

#: snippet 截断长度
_SNIPPET_LEN = 200


def align_citations(text: str, chunks: list[dict]) -> list[dict]:
    """解析 [1][2] 标注，返回 citations 列表。

    chunks 是 rerank 后的 top_n，每个含: id, content, article_slug, heading, score
    返回: [{articleId, title, slug, snippet}]

    规则：
    - 正则匹配 [1] [2] 等数字标注
    - 按 [n] 出现的序号映射到 chunks[n-1]（n 从 1 开始）
    - snippet 取 chunk content 前 200 字符
    - title 用 heading，无 heading 用 article_slug
    - 只返回文本中实际出现的 [n] 对应的 citation
    - 同一 [n] 多次出现只返回一次，按首次出现顺序排列
    - 越界 [n]（n < 1 或 n > len(chunks)）跳过
    """
    if not text or not chunks:
        return []

    seen: set[int] = set()
    citations: list[dict] = []
    for m in _CITATION_RE.finditer(text):
        n = int(m.group(1))
        if n in seen:
            continue
        if n < 1 or n > len(chunks):
            continue
        seen.add(n)
        chunk = chunks[n - 1]
        title = chunk.get("heading") or chunk.get("article_slug") or ""
        snippet = (chunk.get("content") or "")[:_SNIPPET_LEN]
        citations.append({
            "articleId": str(chunk.get("id", "")),
            "title": title,
            "slug": str(chunk.get("article_slug", "")),
            "snippet": snippet,
        })
    return citations
