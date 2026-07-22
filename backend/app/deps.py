"""FastAPI 依赖注入：DB session / Redis / 鉴权 / IP / anon_id。

业务路由通过 Depends 使用这些依赖。
"""
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError
from app.core.security import decode_access_token
from app.db.redis import get_redis
from app.db.session import get_db
from redis.asyncio import Redis


DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_client_ip(request: Request) -> str:
    """提取真实客户端 IP。

    生产经 Nginx：`X-Forwarded-For: <ip>, <proxy>...`，取第一个。
    本地开发 fallback 到 request.client.host。
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "0.0.0.0"


ClientIP = Annotated[str, Depends(get_client_ip)]


def get_anon_id(
    x_session_id: Annotated[str | None, Header()] = None,
) -> str | None:
    """从 X-Session-Id header 提取 anon_id。

    公开问答接口用此区分会话历史与限流。可选依赖。
    """
    return x_session_id


AnonId = Annotated[str | None, Depends(get_anon_id)]


async def require_admin(
    admin_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """后台鉴权依赖：校验 cookie admin_token。

    返回 admin_id（JWT sub）。无 token 或无效抛 AuthError。
    """
    if not admin_token:
        raise AuthError("未登录")
    payload = decode_access_token(admin_token)
    if not payload:
        raise AuthError("登录已失效")
    sub = payload.get("sub")
    if not sub:
        raise AuthError("token 缺少 sub")
    return str(sub)


AdminId = Annotated[str, Depends(require_admin)]
