"""测试 services/rag/citation.py：引用对齐。"""
from app.services.rag.citation import align_citations


def _chunk(idx: int, *, heading="", article_slug="post-1", content="内容片段") -> dict:
    """构造测试用 chunk。"""
    return {
        "id": f"doc1_{idx}",
        "heading": heading,
        "article_slug": article_slug,
        "content": content,
    }


def test_align_empty_text():
    """空文本返回空列表。"""
    assert align_citations("", [_chunk(1)]) == []


def test_align_empty_chunks():
    """无 chunk 返回空列表。"""
    assert align_citations("回答 [1]", []) == []


def test_align_single_citation():
    """单引用 [1] 映射到第一个 chunk。"""
    chunks = [_chunk(1, heading="标题A", content="片段A内容")]
    text = "根据资料[1]，可以得出结论。"
    result = align_citations(text, chunks)
    assert len(result) == 1
    assert result[0]["articleId"] == "doc1_1"
    assert result[0]["title"] == "标题A"
    assert result[0]["slug"] == "post-1"
    assert result[0]["snippet"] == "片段A内容"


def test_align_multiple_citations():
    """多引用 [1][2] 按序映射。"""
    chunks = [
        _chunk(1, heading="标题A", content="片段A"),
        _chunk(2, heading="标题B", content="片段B"),
    ]
    text = "前半部分见[1]，后半部分见[2]。"
    result = align_citations(text, chunks)
    assert len(result) == 2
    assert result[0]["title"] == "标题A"
    assert result[1]["title"] == "标题B"


def test_align_dedup_same_citation():
    """同一 [n] 多次出现只返回一次，按首次出现顺序。"""
    chunks = [_chunk(1, heading="标题A"), _chunk(2, heading="标题B")]
    text = "[2] 提到 X，[1] 提到 Y，[2] 再次强调。"
    result = align_citations(text, chunks)
    # 首次出现顺序：2 在前，1 在后
    assert len(result) == 2
    assert result[0]["title"] == "标题B"
    assert result[1]["title"] == "标题A"


def test_align_out_of_range_skipped():
    """越界 [n]（n > len 或 n < 1）跳过。"""
    chunks = [_chunk(1, heading="标题A")]
    text = "有效[1]，无效[0]，无效[5]。"
    result = align_citations(text, chunks)
    assert len(result) == 1
    assert result[0]["title"] == "标题A"


def test_align_stacked_citations():
    """叠加标注 [1][3] 都生效。"""
    chunks = [
        _chunk(1, heading="标题A"),
        _chunk(2, heading="标题B"),
        _chunk(3, heading="标题C"),
    ]
    text = "这一点[1][3]共同支撑。"
    result = align_citations(text, chunks)
    assert len(result) == 2
    titles = {c["title"] for c in result}
    assert titles == {"标题A", "标题C"}


def test_align_no_citation_in_text():
    """文本中无 [n] 标注返回空。"""
    chunks = [_chunk(1, heading="标题A")]
    text = "这段回答没有引用任何片段。"
    assert align_citations(text, chunks) == []


def test_align_title_fallback_to_slug():
    """无 heading 时 title 回退到 article_slug。"""
    chunks = [_chunk(1, heading="", article_slug="my-post", content="内容")]
    text = "见[1]。"
    result = align_citations(text, chunks)
    assert result[0]["title"] == "my-post"


def test_align_snippet_truncated():
    """snippet 截断到 200 字符。"""
    long_content = "字" * 300
    chunks = [_chunk(1, content=long_content)]
    text = "[1]"
    result = align_citations(text, chunks)
    assert len(result[0]["snippet"]) == 200
