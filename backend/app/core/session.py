"""Redis 会话存储。

登录时把 jti 写入 Redis（TTL=JWT 过期），logout 时删除；
require_admin 校验 JWT 后再校验 Redis 存在性，使 token 可被服务端主动失效。

Key 设计：``session:{jti}`` → ``{admin_id}``，与 JWT payload 的 jti 一一对应。
"""
from __future__ import annotations

from uuid import uuid4

from app.db.redis import redis

#: Redis key 前缀
_SESSION_PREFIX = "session"

#: session 默认 TTL（秒），与 JWT 过期对齐；调用方传入实际剩余时长更精确
_DEFAULT_TTL = 24 * 3600


def _key(jti: str) -> str:
    return f"{_SESSION_PREFIX}:{jti}"


def new_jti() -> str:
    """生成新的 jti（JWT ID）。"""
    return uuid4().hex


async def store_session(jti: str, admin_id: str, ttl: int = _DEFAULT_TTL) -> None:
    """登录成功后写入 session。

    Args:
        jti: JWT payload 中的 jti
        admin_id: 博主 ID（JWT sub）
        ttl: 过期秒数，应与 JWT exp - iat 一致
    """
    await redis.set(_key(jti), admin_id, ex=ttl)


async def revoke_session(jti: str) -> None:
    """登出或强制失效时删除 session。"""
    await redis.delete(_key(jti))


async def is_session_valid(jti: str) -> bool:
    """校验 session 是否仍存活（未被 logout 失效）。"""
    return bool(await redis.exists(_key(jti)))


async def get_session_admin_id(jti: str) -> str | None:
    """读取 session 绑定的 admin_id（可选，用于二次校验）。"""
    val = await redis.get(_key(jti))
    return val if isinstance(val, str) else None
