"""ORM 模型聚合导出。

- 暴露 Base 供 alembic 与 CRUDBase 使用
- 显式导入所有模型子模块，确保 Base.metadata 注册全部表
  （alembic env.py 依赖 `from app.models import Base` 触发模型注册）
"""
from app.models.admin import Admin
from app.models.base import Base, TimestampMixin
from app.models.channel import Channel
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import Chunk, KnowledgeDoc
from app.models.note_link import NoteLink
from app.models.note_template import NoteTemplate
from app.models.persona import Persona
from app.models.post import Post
from app.models.post_view import PostView
from app.models.qa_pair import QaPair
from app.models.settings import SiteSettings

__all__ = [
    "Base",
    "TimestampMixin",
    "Admin",
    "Channel",
    "ChatMessage",
    "ChatSession",
    "Chunk",
    "KnowledgeDoc",
    "NoteLink",
    "NoteTemplate",
    "Persona",
    "Post",
    "PostView",
    "QaPair",
    "SiteSettings",
]
