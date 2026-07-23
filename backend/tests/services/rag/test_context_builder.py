"""测试 services/rag/context_builder.py：上下文组装。"""
from app.services.rag.context_builder import build_context


def test_build_context_empty():
    """空 chunks 返回空串。"""
    assert build_context([]) == ""


def test_build_context_single():
    """单 chunk 格式正确。"""
    chunks = [{"heading": "标题A", "article_slug": "post-1", "content": "内容A"}]
    result = build_context(chunks)
    assert result == "[1] 标题A\n内容A"


def test_build_context_multiple():
    """多 chunk 用空行分隔，序号递增。"""
    chunks = [
        {"heading": "标题A", "content": "内容A"},
        {"heading": "标题B", "content": "内容B"},
    ]
    result = build_context(chunks)
    assert result == "[1] 标题A\n内容A\n\n[2] 标题B\n内容B"


def test_build_context_title_fallback():
    """无 heading 时回退到 article_slug。"""
    chunks = [{"article_slug": "my-post", "content": "内容"}]
    result = build_context(chunks)
    assert result == "[1] my-post\n内容"


def test_build_context_no_title():
    """heading 和 article_slug 都缺失时标题为空。"""
    chunks = [{"content": "内容"}]
    result = build_context(chunks)
    assert result == "[1] \n内容"


def test_build_context_empty_content():
    """content 缺失时按空串处理。"""
    chunks = [{"heading": "标题A"}]
    result = build_context(chunks)
    assert result == "[1] 标题A\n"
