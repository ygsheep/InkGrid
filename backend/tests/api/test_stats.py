"""测试看板统计 API：GET /api/admin/stats/overview。

重点验证 Redis 缓存逻辑（命中/未命中/降级）。
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.stats import StatsTrend


@pytest.fixture
def mock_admin_dep():
    """mock require_admin 依赖。"""
    from app.deps import require_admin
    from app.main import app

    async def _fake_admin():
        return "admin-test-id"

    app.dependency_overrides[require_admin] = _fake_admin
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_dep():
    """mock get_db 依赖。"""
    from app.db.session import get_db
    from app.main import app

    async def _fake_db():
        return AsyncMock()

    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


OVERVIEW_URL = "/api/admin/stats/overview"


@pytest.mark.asyncio
async def test_stats_requires_admin(client):
    """无鉴权 → 401。"""
    resp = await client.get(OVERVIEW_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_overview_cache_hit(client, mock_admin_dep, mock_db_dep):
    """Redis 缓存命中 → 直接返回缓存数据，不查 DB。"""
    cached_data = {
        "code": 0,
        "data": {
            "summary": {"postCount": 99, "questionCount": 50, "knowledgeDocCount": 10, "monthlyViews": 200},
            "trend": {"posts": [1, 2, 3], "questions": [4, 5, 6]},
            "topArticles": [],
            "topQuestions": [],
            "recentQuestions": [],
        },
        "message": "ok",
    }
    with patch("app.api.admin.stats.redis") as mock_redis:
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        resp = await client.get(OVERVIEW_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["summary"]["postCount"] == 99
    assert body["data"]["summary"]["monthlyViews"] == 200
    # Redis get 被调用，set 不应被调用（缓存命中）
    mock_redis.get.assert_called_once()
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_overview_cache_miss_queries_db(client, mock_admin_dep):
    """Redis 缓存未命中 → 查 DB 聚合 + 写入缓存。"""
    from app.db.session import get_db
    from app.main import app

    # mock DB session
    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(side_effect=[5, 10, 3, 20])  # post/q/doc/views

    async def _fake_db():
        return mock_session

    app.dependency_overrides[get_db] = _fake_db

    # mock 聚合查询函数返回空列表
    with patch("app.api.admin.stats._fetch_trend", new_callable=AsyncMock) as mock_trend, \
         patch("app.api.admin.stats._fetch_top_articles", new_callable=AsyncMock) as mock_articles, \
         patch("app.api.admin.stats._fetch_top_questions", new_callable=AsyncMock) as mock_questions, \
         patch("app.api.admin.stats._fetch_recent_questions", new_callable=AsyncMock) as mock_recent, \
         patch("app.api.admin.stats.redis") as mock_redis:

        mock_trend.return_value = StatsTrend(posts=[1, 1], questions=[2, 2])
        mock_articles.return_value = []
        mock_questions.return_value = []
        mock_recent.return_value = []
        mock_redis.get = AsyncMock(return_value=None)  # 缓存未命中
        mock_redis.set = AsyncMock()

        resp = await client.get(OVERVIEW_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["summary"]["postCount"] == 5
    assert body["data"]["summary"]["monthlyViews"] == 20
    # 缓存被写入
    mock_redis.set.assert_called_once()
    set_args = mock_redis.set.call_args
    assert set_args.kwargs.get("ex") == 300  # TTL 5 分钟

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_overview_cache_read_failure_falls_back(client, mock_admin_dep):
    """Redis 读失败 → 降级查 DB，不阻断响应。"""
    from app.db.session import get_db
    from app.main import app

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(side_effect=[1, 1, 1, 1])

    async def _fake_db():
        return mock_session

    app.dependency_overrides[get_db] = _fake_db

    with patch("app.api.admin.stats._fetch_trend", new_callable=AsyncMock) as mock_trend, \
         patch("app.api.admin.stats._fetch_top_articles", new_callable=AsyncMock) as mock_a, \
         patch("app.api.admin.stats._fetch_top_questions", new_callable=AsyncMock) as mock_q, \
         patch("app.api.admin.stats._fetch_recent_questions", new_callable=AsyncMock) as mock_r, \
         patch("app.api.admin.stats.redis") as mock_redis:

        mock_trend.return_value = StatsTrend(posts=[], questions=[])
        mock_a.return_value = []
        mock_q.return_value = []
        mock_r.return_value = []
        # Redis 读抛异常
        mock_redis.get = AsyncMock(side_effect=Exception("redis down"))
        mock_redis.set = AsyncMock(side_effect=Exception("redis down"))

        resp = await client.get(OVERVIEW_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    # 仍然返回了 DB 数据
    assert body["data"]["summary"]["postCount"] == 1

    app.dependency_overrides.clear()
