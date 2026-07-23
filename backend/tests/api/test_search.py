"""测试公开搜索 API：GET /api/search + /api/search/suggestions。

使用 dependency_overrides mock DB，patch search_posts / get_settings。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db_dep():
    """mock get_db 依赖，返回 AsyncMock session。"""
    from app.db.session import get_db
    from app.main import app

    async def _fake_db():
        session = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        return session

    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


SEARCH_URL = "/api/search"
SUGGEST_URL = "/api/search/suggestions"


@pytest.mark.asyncio
async def test_search_rejects_empty_q(client, mock_db_dep):
    """q 为空 → 422（Query min_length=1）。"""
    resp = await client.get(SEARCH_URL, params={"q": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_meili_disabled(client, mock_db_dep):
    """meili_enabled=False → 返回空结果（降级）。"""
    with patch("app.api.public.search.get_settings") as mock_settings:
        mock_settings.return_value.meili_enabled = False
        resp = await client.get(SEARCH_URL, params={"q": "test"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["hits"] == []
    assert body["data"]["estimatedTotalHits"] == 0


@pytest.mark.asyncio
async def test_search_returns_hits(client, mock_db_dep):
    """正常搜索 → 返回高亮命中（mock search_posts）。"""
    mock_raw = {
        "hits": [
            {
                "id": "post-1",
                "slug": "hello-world",
                "title": "Hello World",
                "excerpt": "测试摘要",
                "channel_slug": "blog",
                "channel_name": "博客",
                "tags": ["test"],
                "published_at": 1700000000,
                "reading_time": 5,
                "_formatted": {
                    "title": "<mark>Hello</mark> World",
                    "excerpt": "测试摘要",
                    "content": "# <mark>Hello</mark>",
                },
            }
        ],
        "estimatedTotalHits": 1,
        "processingTimeMs": 2,
        "query": "Hello",
    }
    with patch("app.api.public.search.search_posts", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_raw
        with patch("app.api.public.search.get_settings") as mock_settings:
            mock_settings.return_value.meili_enabled = True
            resp = await client.get(SEARCH_URL, params={"q": "Hello", "limit": 5})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    hits = body["data"]["hits"]
    assert len(hits) == 1
    assert hits[0]["slug"] == "hello-world"
    assert hits[0]["_formatted"]["title"] == "<mark>Hello</mark> World"
    assert body["data"]["estimatedTotalHits"] == 1
    # 验证 search_posts 被正确调用
    mock_search.assert_called_once_with("Hello", limit=5, channel_slug=None)


@pytest.mark.asyncio
async def test_search_with_channel_filter(client, mock_db_dep):
    """channel 过滤 → search_posts 收到 channel_slug。"""
    with patch("app.api.public.search.search_posts", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"hits": [], "estimatedTotalHits": 0}
        with patch("app.api.public.search.get_settings") as mock_settings:
            mock_settings.return_value.meili_enabled = True
            resp = await client.get(
                SEARCH_URL, params={"q": "test", "channel": "tech"}
            )

    assert resp.status_code == 200
    mock_search.assert_called_once_with("test", limit=10, channel_slug="tech")


@pytest.mark.asyncio
async def test_suggestions_returns_data(client, mock_db_dep):
    """suggestions 端点 → 返回热门文章（mock DB）。"""
    from app.db.session import get_db
    from app.main import app

    # 构造 mock DB 返回值
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        ("hello-world", "Hello World", 5),
        ("second-post", "Second Post", 2),
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _fake_db():
        return mock_session

    app.dependency_overrides[get_db] = _fake_db

    resp = await client.get(SUGGEST_URL, params={"limit": 5})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    items = body["data"]["suggestions"]
    assert len(items) == 2
    assert items[0]["slug"] == "hello-world"
    assert items[0]["title"] == "Hello World"
    assert items[0]["views"] == 5
    assert items[1]["views"] == 2

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_no_auth_required(client, mock_db_dep):
    """search 是公开 API，不需要登录。"""
    with patch("app.api.public.search.get_settings") as mock_settings:
        mock_settings.return_value.meili_enabled = False
        resp = await client.get(SEARCH_URL, params={"q": "test"})
    # 不应该返回 401
    assert resp.status_code != 401
