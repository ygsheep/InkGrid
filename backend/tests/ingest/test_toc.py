"""测试 ingest/toc.py:从 ParsedDoc.headings 生成 TocItem 列表。"""
from app.ingest.parser import parse_markdown
from app.ingest.toc import headings_to_toc


def test_toc_empty():
    """无标题 → 空 toc。"""
    parsed = parse_markdown("T", "纯文本")
    assert headings_to_toc(parsed.headings) == []


def test_toc_basic():
    """基本标题层级转 TocItem。"""
    content = "# 一级\n## 二级\n### 三级"
    parsed = parse_markdown("T", content)
    toc = headings_to_toc(parsed.headings)
    assert len(toc) == 3
    assert toc[0] == {"id": "一级", "title": "一级", "level": 1}
    assert toc[1] == {"id": "二级", "title": "二级", "level": 2}
    assert toc[2] == {"id": "三级", "title": "三级", "level": 3}


def test_toc_dedup_ids():
    """重复标题:第二个 id 加 -2 后缀。"""
    content = "# 标题\n# 标题\n# 标题"
    parsed = parse_markdown("T", content)
    toc = headings_to_toc(parsed.headings)
    ids = [item["id"] for item in toc]
    assert ids == ["标题", "标题-2", "标题-3"]


def test_toc_preserves_text():
    """title 保留原文(含空格/标点)。"""
    content = "# Hello, World!"
    parsed = parse_markdown("T", content)
    toc = headings_to_toc(parsed.headings)
    assert toc[0]["title"] == "Hello, World!"
    assert toc[0]["id"] == "hello-world"
