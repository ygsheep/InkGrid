"""后台 API 路由聚合（需鉴权，除 login）。"""
from fastapi import APIRouter

from app.api.admin import auth, channels, knowledge, personas, posts, settings, stats, uploads

router = APIRouter()
router.include_router(auth.router)
router.include_router(posts.router)
router.include_router(channels.router)
router.include_router(personas.router)
router.include_router(knowledge.router)
router.include_router(settings.router)
router.include_router(stats.router)
router.include_router(uploads.router)

__all__ = ["router"]
