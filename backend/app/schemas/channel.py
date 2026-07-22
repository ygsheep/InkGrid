"""频道请求/响应 schema。"""
from pydantic import BaseModel, ConfigDict


class ChannelBase(BaseModel):
    slug: str
    name: str
    description: str | None = None
    accent: str | None = None


class ChannelCreate(ChannelBase):
    persona_id: str | None = None  # UUID 字符串


class ChannelUpdate(BaseModel):
    slug: str | None = None
    name: str | None = None
    description: str | None = None
    accent: str | None = None
    persona_id: str | None = None


class Channel(ChannelBase):
    """频道响应（与前端 Channel 类型对齐）。"""

    model_config = ConfigDict(from_attributes=True)

    persona: str | None = None  # 人设提示，简化输出
    postCount: int = 0


class ChannelDetail(Channel):
    """频道详情（含人设摘要等）。"""

    pass
