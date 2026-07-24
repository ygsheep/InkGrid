"""CRUD 层统一导出。

P0 阶段范围：base + post + channel + persona + chat + admin。
knowledge / policy / stats 留作 P1+ 扩展占位。
"""
from app.crud import admin as admin_crud
from app.crud.base import CRUDBase
from app.crud.channel import channel
from app.crud.chat import chat_message, chat_session
from app.crud.persona import persona
from app.crud.post import post
from app.crud import qa as qa_crud

__all__ = [
    "admin_crud",
    "CRUDBase",
    "post",
    "channel",
    "persona",
    "chat_session",
    "chat_message",
    "qa_crud",
]
