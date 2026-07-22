"""测试 /health 端点。

需要 app 实例化（不依赖 DB）。
"""
import pytest


@pytest.mark.asyncio
async def test_health(client):
    """GET /health 返回 200 + envelope。"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert body["message"] == "ok"
