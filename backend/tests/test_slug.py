"""测试 utils/slug.py:slug 生成。"""
from app.utils.slug import slugify


def test_slugify_ascii():
    """纯 ASCII:转小写、空格转连字符。"""
    assert slugify("Hello World") == "hello-world"


def test_slugify_chinese():
    """中文:P0 简化保留非 ASCII 字符原样,通过冲突后缀保证唯一性。"""
    assert slugify("我的第一篇文章") == "我的第一篇文章"


def test_slugify_mixed():
    """中英混合。"""
    assert slugify("React 入门 Guide") == "react-入门-guide"


def test_slugify_special_chars():
    """特殊字符:替换为连字符,合并连续连字符。"""
    assert slugify("Hello!!! World???") == "hello-world"


def test_slugify_leading_trailing_hyphens():
    """首尾连字符去除。"""
    assert slugify("---hello---") == "hello"


def test_slugify_empty():
    """空字符串返回空。"""
    assert slugify("") == ""


def test_slugify_max_length():
    """超过 120 字符截断(Post.slug 限制 120)。"""
    long_title = "a" * 200
    result = slugify(long_title)
    assert len(result) <= 120
    assert result == "a" * 120


def test_slugify_preserves_digits():
    """数字保留。"""
    assert slugify("Post 2024 v2") == "post-2024-v2"
