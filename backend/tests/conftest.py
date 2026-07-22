"""pytest fixtures：mock settings + 测试 client + 单元测试辅助。

P0 阶段以单元测试为主（不依赖 PG/Redis）；
集成测试需要 docker compose 起 PG/Redis，留作扩展。
"""
import asyncio
import os
from collections.abc import AsyncGenerator

# 设置测试环境变量（在 import app 之前）
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://inkgrid:inkgrid@localhost:5432/inkgrid_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")  # 测试用 db 15

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

# 触发配置加载（@lru_cache）
from app.config import get_settings  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    """session 级 event loop。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def settings():
    """返回测试 settings。"""
    return get_settings()


@pytest.fixture(scope="session")
def anyio_backend():
    """pytest-asyncio 后端。"""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """测试 HTTP client（不依赖 DB，纯 ASGI）。

    需要 DB 的集成测试应自行起 session 或用 docker compose。
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
