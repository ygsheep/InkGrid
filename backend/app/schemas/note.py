"""知识库笔记相关 Schema：NoteDTO、目录树、模板、反链。

入参（创建/更新）复用 app.schemas.post.PostCreate / PostUpdate，
二者已包含 category/folder_path/is_moc/source_url 等知识库字段。
"""
from pydantic import BaseModel, ConfigDict


class NoteDTO(BaseModel):
    """笔记/文章统一 DTO（知识库视图）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    excerpt: str | None = None
    content_md: str
    category: str
    folder_path: str | None = None
    is_moc: bool = False
    source_url: str | None = None
    owner_id: str | None = None
    channel_id: str | None = None
    channel_slug: str | None = None
    channel_name: str | None = None
    tags: list[str] = []
    status: str
    published_at: str | None = None
    reading_time: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class NoteListItem(BaseModel):
    """笔记列表项（不含正文，轻量）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    excerpt: str | None = None
    category: str
    folder_path: str | None = None
    is_moc: bool = False
    tags: list[str] = []
    status: str
    published_at: str | None = None
    updated_at: str | None = None


class NoteLinkDTO(BaseModel):
    """出链/反链项。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    target_note_id: str | None = None
    target_title_raw: str
    # 反链方向才有的信息（出链查询时为空）
    source_note_id: str | None = None
    source_title: str | None = None


class NoteTreeFolder(BaseModel):
    """目录树子文件夹节点。"""

    key: str  # 完整 folder_path，如 "knowledge/大模型"
    label: str  # 显示名，如 "大模型"
    count: int


class NoteTreeNode(BaseModel):
    """目录树顶层 category 节点。"""

    key: str  # category，如 "knowledge"
    label: str  # 显示名，如 "主题知识"
    code: str  # 目录前缀，如 "03_Knowledge"
    count: int
    children: list[NoteTreeFolder] = []


class NoteTemplateDTO(BaseModel):
    """笔记模板。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    description: str | None = None
    content_md: str
    created_at: str | None = None
    updated_at: str | None = None


class NoteTemplateCreate(BaseModel):
    """新建模板入参。"""

    name: str
    category: str
    description: str | None = None
    content_md: str
