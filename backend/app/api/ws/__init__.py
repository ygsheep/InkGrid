"""WebSocket 路由聚合。

P0：chat（文字流，mock LLM）。
P2：voice（语音流，留作扩展）。
"""
from fastapi import APIRouter

from app.api.ws import chat

router = APIRouter()
router.include_router(chat.router)

__all__ = ["router"]
