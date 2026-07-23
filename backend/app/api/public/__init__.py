"""公开 API 路由聚合（无需登录）。"""
from fastapi import APIRouter

from app.api.public import about, channels, chat_sessions, personas, posts, search, tags

router = APIRouter()
router.include_router(posts.router)
router.include_router(tags.router)
router.include_router(channels.router)
router.include_router(personas.router)
router.include_router(about.router)
router.include_router(chat_sessions.router)
router.include_router(search.router)

__all__ = ["router"]
