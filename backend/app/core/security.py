"""密码哈希（argon2）+ JWT 签发与校验 + admin_token cookie 工具。

P0 阶段只做博主后台鉴权：登录、签发 JWT、cookie 读写。
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Response

from app.config import get_settings

_settings = get_settings()
_hasher = PasswordHasher()

#: cookie 属性
COOKIE_NAME = _settings.cookie_name
COOKIE_MAX_AGE = _settings.jwt_expire_hours * 3600


def hash_password(plain: str) -> str:
    """argon2 哈希密码。"""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码。"""
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(sub: str, extra: dict | None = None) -> str:
    """签发 JWT。sub 通常是 admin_id。"""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(hours=_settings.jwt_expire_hours),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """解码 JWT，失败返回 None。"""
    try:
        return jwt.decode(
            token,
            _settings.jwt_secret,
            algorithms=[_settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return None


def set_auth_cookie(response: Response, token: str) -> None:
    """写 admin_token cookie。HttpOnly + Secure + SameSite=Lax。

    SameSite 选 Lax 而非 Strict 的原因：
    - 前端 :3000 与后端 :8000 跨端口，浏览器视 localhost:3000→localhost:8000 的
      XHR/fetch 为 same-site 跨端口请求；Strict 在部分浏览器的客户端导航 RSC
      fetch 中不被携带，导致 middleware 读不到 cookie 而 redirect /login。
    - Lax 是现代浏览器默认值，same-site 请求会携带，兼容性最好。
    - 后台 cookie 仅用于同站 admin 鉴权，Lax 足够安全。
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=not _settings.debug,  # 开发期允许 http
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """清除 admin_token cookie。"""
    response.delete_cookie(key=COOKIE_NAME, path="/")
