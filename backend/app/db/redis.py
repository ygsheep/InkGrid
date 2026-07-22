"""Redis 连接池 + 健康检查。"""
from redis.asyncio import Redis, from_url

from app.config import get_settings

settings = get_settings()

redis: Redis = from_url(
    settings.redis_url,
    decode_responses=True,
    encoding="utf-8",
    max_connections=20,
)


async def get_redis() -> Redis:
    """FastAPI 依赖：返回全局 Redis 连接。"""
    return redis


async def close_redis() -> None:
    """应用关闭时释放连接池。"""
    await redis.aclose()
