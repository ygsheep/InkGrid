"""测试 ingest/parser.py：Markdown 解析。"""
from app.ingest.parser import parse_markdown


def test_parse_markdown_no_headings():
    """无标题文。"""
    parsed = parse_markdown("测试", "纯文本内容，无标题。")
    assert parsed.title == "测试"
    assert parsed.text == "纯文本内容，无标题。"
    assert parsed.headings == []


def test_parse_markdown_with_headings():
    """提取 # 标题层级。"""
    content = "# 一级标题\n正文\n## 二级标题\n正文二\n### 三级\n内容"
    parsed = parse_markdown("测试", content, slug="test")
    assert len(parsed.headings) == 3
    assert parsed.headings[0] == {"level": 1, "text": "一级标题", "position": 0}
    assert parsed.headings[1] == {"level": 2, "text": "二级标题", "position": 2}
    assert parsed.headings[2] == {"level": 3, "text": "三级", "position": 4}
    assert parsed.slug == "test"


def test_parse_markdown_preserves_text():
    """原文保留。"""
    content = "# 标题\n\n段落一。\n\n段落二。"
    parsed = parse_markdown("T", content)
    assert parsed.text == content


def test_parse_markdown_heading_levels():
    """1-6 级标题都识别。"""
    content = "# L1\n## L2\n### L3\n#### L4\n##### L5\n###### L6"
    parsed = parse_markdown("T", content)
    levels = [h["level"] for h in parsed.headings]
    assert levels == [1, 2, 3, 4, 5, 6]


def test_parse_markdown_no_heading_inline_hash():
    """行内 # 不被识别为标题。"""
    content = "段落中的 # 不是 标题"
    parsed = parse_markdown("T", content)
    assert parsed.headings == []
