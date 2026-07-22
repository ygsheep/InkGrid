"""测试 schemas/post.py：字段映射与序列化。"""
from datetime import datetime, timezone

from app.schemas.post import Article, ArticleSummary, TocItem


def test_article_summary_camel_case():
    """ArticleSummary 用 camelCase（与前端对齐）。"""
    s = ArticleSummary(
        id="abc",
        slug="hello",
        title="Hello",
        excerpt="excerpt",
        channel="blog",
        channelName="博客",
        tags=["a", "b"],
        publishedAt="2026-01-01T00:00:00+00:00",
        readingTime=5,
    )
    assert s.id == "abc"
    assert s.channel == "blog"
    assert s.channelName == "博客"
    assert s.publishedAt == "2026-01-01T00:00:00+00:00"
    assert s.readingTime == 5


def test_article_summary_optional_excerpt():
    """excerpt 可为空。"""
    s = ArticleSummary(
        id="x",
        slug="x",
        title="X",
        channel="blog",
        channelName="博客",
        publishedAt="2026-01-01T00:00:00+00:00",
    )
    assert s.excerpt is None
    assert s.tags is None
    assert s.readingTime is None


def test_article_extends_summary():
    """Article 含 content / html / toc。"""
    a = Article(
        id="x",
        slug="x",
        title="X",
        channel="blog",
        channelName="博客",
        publishedAt="2026-01-01T00:00:00+00:00",
        content="# Hello",
        html="<h1>Hello</h1>",
        toc=[TocItem(id="h1", title="Hello", level=1)],
    )
    assert a.content == "# Hello"
    assert a.html == "<h1>Hello</h1>"
    assert a.toc[0].id == "h1"
    assert a.toc[0].level == 1


def test_toc_item():
    """TocItem 字段。"""
    t = TocItem(id="section-1", title="第一章", level=2)
    assert t.id == "section-1"
    assert t.title == "第一章"
    assert t.level == 2


def test_article_summary_iso_date():
    """publishedAt 是 ISO 字符串。"""
    now = datetime.now(timezone.utc)
    s = ArticleSummary(
        id="x",
        slug="x",
        title="X",
        channel="blog",
        channelName="博客",
        publishedAt=now.isoformat(),
    )
    assert "T" in s.publishedAt
    assert "+" in s.publishedAt or s.publishedAt.endswith("Z")
