"""文档解析：Markdown 直接取文本，PDF/DOCX 留作 P1。

P0 阶段只处理文章（Markdown 源码），返回纯文本 + 标题元信息。
"""
from dataclasses import dataclass


@dataclass
class ParsedDoc:
    """解析结果。"""

    title: str
    text: str
    headings: list[dict]  # [{level, text, position}]
    slug: str | None = None


def parse_markdown(title: str, content_md: str, slug: str | None = None) -> ParsedDoc:
    """解析 Markdown：直接取文本，按 # 提取标题层级。

    P0 简化：不做完整 AST，只用正则提取 # 标题作为分块边界提示。
    position 是字符偏移量（行首在 content_md 中的位置），供 chunker 按字符切片。
    """
    import re

    headings: list[dict] = []
    offset = 0
    for line in content_md.splitlines(keepends=True):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*\r?\n?$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            headings.append({"level": level, "text": text, "position": offset})
        offset += len(line)

    return ParsedDoc(
        title=title,
        text=content_md,
        headings=headings,
        slug=slug,
    )
