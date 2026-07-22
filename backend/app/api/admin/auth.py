"""后台鉴权路由：POST /auth/login, /auth/logout, GET /auth/me。"""
from fastapi import APIRouter, Response

from app.core.errors import AuthError
from app.core.logging import get_logger
from app.core.rate_limit import check_admin_login
from app.core.security import (
    clear_auth_cookie,
    create_access_token,
    set_auth_cookie,
    verify_password,
)
from app.crud import admin as admin_crud
from app.deps import AdminId, ClientIP, DBSession
from app.schemas.auth import AdminInfo, LoginRequest
from app.schemas.common import envelope

router = APIRouter(prefix="/auth")
logger = get_logger("admin.auth")


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    db: DBSession,
    ip: ClientIP,
) -> dict:
    """登录：校验密码，签发 JWT，写 cookie。"""
    # 限流：按 IP 5 次/min
    await check_admin_login(ip)

    admin = await admin_crud.get_by_username(db, payload.username)
    if not admin or not verify_password(payload.password, admin.password_hash):
        # 不区分用户不存在/密码错误
        logger.warning("login_failed", username=payload.username, ip=ip)
        raise AuthError("用户名或密码错误")

    token = create_access_token(str(admin.id), extra={"username": admin.username})
    set_auth_cookie(response, token)
    logger.info("login_ok", admin_id=str(admin.id), ip=ip)
    return envelope(AdminInfo(id=str(admin.id), username=admin.username).model_dump())


@router.post("/logout")
async def logout(response: Response) -> dict:
    """登出：清 cookie。"""
    clear_auth_cookie(response)
    return envelope({"ok": True})


@router.get("/me")
async def me(admin_id: AdminId, db: DBSession) -> dict:
    """当前博主信息（依赖 require_admin）。"""
    admin = await admin_crud.get(db, admin_id)
    if not admin:
        raise AuthError("账号不存在")
    return envelope(AdminInfo(id=str(admin.id), username=admin.username).model_dump())
