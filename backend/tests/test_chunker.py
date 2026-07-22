"""测试 ingest/chunker.py：分块逻辑。"""
from app.ingest.chunker import chunk_document, _estimate_tokens
from app.ingest.parser import ParsedDoc


def test_estimate_tokens_chinese():
    """中文按 1:1。"""
    assert _estimate_tokens("你好世界") == 4


def test_estimate_tokens_english():
    """英文按 4:1。"""
    # 8 字符 → 2 token
    assert _estimate_tokens("abcdefgh") == 2


def test_estimate_tokens_mixed():
    """中英混合。"""
    # 2 中文 + 4 英文 = 2 + 1 = 3
    assert _estimate_tokens("你好abcd") == 3


def test_chunk_short_document():
    """短文不分块，单块。"""
    parsed = ParsedDoc(
        title="测试",
        text="这是一段简短的内容。",
        headings=[],
        slug="test",
    )
    chunks = chunk_document(parsed, tags=["t"])
    assert len(chunks) == 1
    assert chunks[0].seq == 0
    assert "简短" in chunks[0].content
    assert chunks[0].metadata["article_slug"] == "test"
    assert chunks[0].metadata["tags"] == ["t"]


def test_chunk_with_headings():
    """有标题时分段。"""
    content = "# 标题一\n内容一\n\n## 标题二\n内容二"
    parsed = ParsedDoc(
        title="测试",
        text=content,
        headings=[
            {"level": 1, "text": "标题一", "position": 0},
            {"level": 2, "text": "标题二", "position": 4},
        ],
        slug="test",
    )
    chunks = chunk_document(parsed)
    # 至少分两块（标题一/标题二）
    assert len(chunks) >= 2
    headings = [c.metadata.get("heading") for c in chunks]
    assert "标题一" in headings or "标题二" in headings


def test_chunk_long_section_sliding_window():
    """长段落用滑窗切分。"""
    long_text = "a" * 2000  # 2000 字符，远超 TARGET_CHARS
    parsed = ParsedDoc(title="长文", text=long_text, headings=[], slug="long")
    chunks = chunk_document(parsed)
    assert len(chunks) > 1
    # 每块不超过 TARGET_CHARS
    for c in chunks:
        assert len(c.content) <= 700


def test_chunk_empty_document():
    """空文不分块。"""
    parsed = ParsedDoc(title="", text="", headings=[], slug="empty")
    chunks = chunk_document(parsed)
    assert chunks == []
