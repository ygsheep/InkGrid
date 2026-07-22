"""分块：按标题层级 + 滑窗，目标 350 token/块，重叠 50 token。

P0 简化：
- token 计数用字符数粗略估算（中文 1 字 ≈ 1 token，英文 4 字符 ≈ 1 token）
- 按段落（空行分隔）+ 标题边界切分
- 超长段落再用滑窗切

P1 阶段接入 tiktoken 精确计数。
"""
from dataclasses import dataclass

from app.ingest.parser import ParsedDoc

# 目标块大小（粗略字符数）
TARGET_CHARS = 700  # 约 350 token
OVERLAP_CHARS = 100  # 约 50 token


@dataclass
class ChunkResult:
    """单个分块结果。"""

    seq: int
    content: str
    token_count: int
    metadata: dict


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文按 1:1，英文按 4:1。"""
    cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    en_chars = len(text) - cn
    return cn + en_chars // 4


def chunk_document(parsed: ParsedDoc, tags: list[str] | None = None) -> list[ChunkResult]:
    """按标题边界 + 滑窗分块。

    - 先按 ## / ### 标题切大段
    - 段落 > TARGET_CHARS 用滑窗再切
    - 保留 heading 元信息写入 metadata
    """
    text = parsed.text
    headings = parsed.headings

    # 按标题位置切段
    sections: list[tuple[str, str]] = []  # (heading_text, section_text)
    if not headings:
        sections.append(("", text))
    else:
        prev_pos = 0
        prev_heading = ""
        for h in headings:
            pos = h["position"]
            if pos > prev_pos:
                sections.append((prev_heading, text[prev_pos:pos]))
            prev_heading = h["text"]
            prev_pos = pos
        # 最后一段
        if prev_pos < len(text):
            sections.append((prev_heading, text[prev_pos:]))

    chunks: list[ChunkResult] = []
    seq = 0
    for heading, section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= TARGET_CHARS:
            chunks.append(_make_chunk(seq, section, heading, parsed, tags))
            seq += 1
        else:
            # 滑窗切分
            for start in range(0, len(section), TARGET_CHARS - OVERLAP_CHARS):
                piece = section[start : start + TARGET_CHARS]
                if not piece.strip():
                    break
                chunks.append(_make_chunk(seq, piece, heading, parsed, tags))
                seq += 1
                if start + TARGET_CHARS >= len(section):
                    break

    return chunks


def _make_chunk(
    seq: int, content: str, heading: str, parsed: ParsedDoc, tags: list[str] | None
) -> ChunkResult:
    """构造单个 ChunkResult。"""
    metadata = {
        "article_slug": parsed.slug,
        "heading": heading or None,
        "tags": tags or [],
    }
    # 清掉 None 键
    metadata = {k: v for k, v in metadata.items() if v is not None}
    return ChunkResult(
        seq=seq,
        content=content,
        token_count=_estimate_tokens(content),
        metadata=metadata,
    )
