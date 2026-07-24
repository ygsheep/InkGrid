"""FastAPI 依赖注入：DB session / Redis / 鉴权 / IP / anon_id。

业务路由通过 Depends 使用这些依赖。
"""
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError
from app.core.security import decode_access_token
from app.core.session import is_session_valid
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

    流程：① JWT 解码（签名+过期）→ ② 若 payload 含 jti，校验 Redis session 存在性。
    返回 admin_id（JWT sub）。无 token 或无效抛 AuthError。

    jti 校验使 logout 可立即失效 token（删 Redis key），无需等待 JWT 自然过期。
    无 jti 的旧 token 仅做 JWT 校验，向后兼容。
    """
    if not admin_token:
        raise AuthError("未登录")
    payload = decode_access_token(admin_token)
    if not payload:
        raise AuthError("登录已失效")
    sub = payload.get("sub")
    if not sub:
        raise AuthError("token 缺少 sub")
    # 若 token 带 jti，必须校验 Redis session 存活（支持 logout 主动失效）
    jti = payload.get("jti")
    if jti:
        if not await is_session_valid(jti):
            raise AuthError("会话已失效，请重新登录")
    return str(sub)


AdminId = Annotated[str, Depends(require_admin)]
