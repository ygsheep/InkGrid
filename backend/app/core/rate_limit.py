"""限流：Redis 滑动窗口 + 计数器，按 IP / anon_id / 接口分级。

层级（P0 范围）：
| 维度    | 用途     | 限制            | 实现        |
|---------|----------|-----------------|-------------|
| IP      | 全局     | 60 req/min      | 滑动窗口    |
| IP      | 问答     | 20 问/min       | 滑动窗口    |
| anon_id | 问答     | 50 问/天        | 计数器      |
| 后台    | 登录     | 5 次/min        | 计数器      |

超限抛 RateLimitError（429），含 reset_at 与 remaining。
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.errors import RateLimitError
from app.db.redis import redis


def _key(*parts: str) -> str:
    """构造限流 key：rate:{scope}:{id}:{window}。"""
    return "rate:" + ":".join(parts)


async def sliding_window(
    *,
    scope: str,
    identifier: str,
    limit: int,
    window_sec: int,
) -> None:
    """Redis ZSET 滑动窗口限流。

    - scope: 业务标识（如 "ip_global"、"chat_ip"）
    - identifier: 限流对象（IP / anon_id）
    - limit: 窗口内最大请求数
    - window_sec: 窗口秒数

    超限抛 RateLimitError。
    """
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    window_start = now_ts - window_sec
    member = f"{now_ts}:{uuid4().hex}"
    key = _key(scope, identifier)

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # 清理过期
    pipe.zadd(key, {member: now_ts})
    pipe.zcard(key)
    pipe.expire(key, window_sec + 10)
    _, _, count, _ = await pipe.execute()

    if count > limit:
        reset_at = (now + timedelta(seconds=window_sec)).isoformat()
        raise RateLimitError(
            "请求过于频繁，请稍后再试",
            reset_at=reset_at,
            remaining=0,
        )


async def fixed_counter(
    *,
    scope: str,
    identifier: str,
    limit: int,
    window_sec: int,
) -> None:
    """Redis 计数器限流（INCR + EXPIRE 首次）。

    适合按天计数类（如 anon_id 每日问答）。
    """
    key = _key(scope, identifier)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_sec)
    if count > limit:
        ttl = await redis.ttl(key)
        reset_at = (
            datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 0))
        ).isoformat()
        raise RateLimitError(
            "今日额度已用尽",
            reset_at=reset_at,
            remaining=max(limit - count + 1, 0),
        )


async def check_ip_global(ip: str, limit: int = 60, window_sec: int = 60) -> None:
    """IP 全局限流：60 req/min。"""
    await sliding_window(
        scope="ip_global",
        identifier=ip,
        limit=limit,
        window_sec=window_sec,
    )


async def check_chat_ip(ip: str, limit: int = 20, window_sec: int = 60) -> None:
    """IP 问答限流：20 问/min。"""
    await sliding_window(
        scope="chat_ip",
        identifier=ip,
        limit=limit,
        window_sec=window_sec,
    )


async def check_chat_anon(
    anon_id: str, limit: int = 50, window_sec: int = 86400
) -> None:
    """anon_id 问答限流：50 问/天。"""
    await fixed_counter(
        scope="chat_anon",
        identifier=anon_id,
        limit=limit,
        window_sec=window_sec,
    )


async def check_admin_login(
    identifier: str, limit: int = 5, window_sec: int = 60
) -> None:
    """后台登录限流：5 次/min（按 IP 或用户名）。"""
    await fixed_counter(
        scope="admin_login",
        identifier=identifier,
        limit=limit,
        window_sec=window_sec,
    )
