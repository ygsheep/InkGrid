"""会话与消息 schema。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Citation(BaseModel):
    """引用溯源：与前端 Citation 对齐。"""

    articleId: str
    title: str
    slug: str
    snippet: str


class ChatScope(BaseModel):
    """问答范围。"""

    type: str  # global|channel|article
    refId: str | None = None


class ChatSessionCreate(BaseModel):
    """创建会话入参。"""

    anon_id: str | None = None
    persona_id: UUID | None = None
    scope_type: str = "global"
    scope_ref: str | None = None
    title: str | None = None


class ChatSessionOut(BaseModel):
    """会话响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    anon_id: str | None = None
    persona_id: str | None = None
    scope_type: str
    scope_ref: str | None = None
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatMessageOut(BaseModel):
    """消息响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    citations: list[Citation] | None = None
    follow_ups: list[str] | None = None
    created_at: datetime
