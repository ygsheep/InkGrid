"""文章请求/响应 schema。与前端 web/types/index.ts 对齐。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TocItem(BaseModel):
    id: str
    title: str
    level: int


class ArticleSummary(BaseModel):
    """文章列表项（与前端 ArticleSummary 对齐）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    excerpt: str | None = None
    channel: str  # 频道 slug
    channelName: str  # 频道名
    tags: list[str] | None = None
    publishedAt: str  # ISO 日期
    readingTime: int | None = None


class Article(ArticleSummary):
    """文章详情（含正文与目录）。"""

    content: str  # Markdown 源码
    html: str | None = None
    toc: list[TocItem] = []


class PostCreate(BaseModel):
    """后台写文章/笔记入参。

    channel_id 可空：未发布的私有笔记（inbox/daily/...）无频道。
    category 默认 inbox：新建笔记默认进收集箱，笔者后续整理。
    """

    slug: str = ""
    title: str
    excerpt: str | None = None
    content_md: str
    channel_id: UUID | None = None
    category: str = "inbox"
    folder_path: str | None = None
    is_moc: bool = False
    source_url: str | None = None
    tags: list[str] | None = None
    status: str = "draft"
    reading_time: int | None = None
    toc: list[TocItem] | None = None


class PostUpdate(BaseModel):
    """后台更新文章/笔记入参（全字段可选）。"""

    slug: str | None = None
    title: str | None = None
    excerpt: str | None = None
    content_md: str | None = None
    channel_id: UUID | None = None
    category: str | None = None
    folder_path: str | None = None
    is_moc: bool | None = None
    source_url: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    reading_time: int | None = None
    toc: list[TocItem] | None = None


class PostStatusUpdate(BaseModel):
    """仅切换状态（发布/草稿/归档）。"""

    status: str


class ArticleAdmin(BaseModel):
    """后台文章响应（含 status / channel_id / created_at 等内部字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    excerpt: str | None = None
    content: str
    html: str | None = None
    channel_id: str
    channel_slug: str | None = None
    channel_name: str | None = None
    tags: list[str] | None = None
    status: str
    published_at: str | None = None
    reading_time: int | None = None
    toc: list[TocItem] = []
    created_at: str | None = None
    updated_at: str | None = None
