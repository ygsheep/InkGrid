"""知识库文档与上传 schema。

对应后端设计 §5.3 的 admin 接口：
- GET    /admin/knowledge/docs              文档列表（含入库状态）
- GET    /admin/knowledge/docs/:id          文档详情
- POST   /admin/knowledge/upload            多文件多格式上传
- GET    /admin/knowledge/docs/:id/download 下载源文件
- DELETE /admin/knowledge/docs/:id          删除文档
- POST   /admin/knowledge/docs/:id/reindex  重建单文档向量
- POST   /admin/knowledge/rebuild           全量重建（异步任务）

响应字段与前端 web/lib/api/admin.ts 的 KnowledgeDoc 类型对齐。
"""
from pydantic import BaseModel, ConfigDict


class KnowledgeDocOut(BaseModel):
    """知识库文档响应（admin 列表项）。

    status 取值：pending | indexed | partial | failed
    - pending: 新建，分块进行中
    - indexed: 解析→分块→写 PG→embedding→写 Milvus 全部成功
    - partial: PG chunks 成功但 Milvus 失败（PG 有 chunks 缺向量）
    - failed: 解析 / 分块失败
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: str  # article | upload | policy
    source_id: str | None = None
    title: str
    raw_uri: str | None = None
    # 上传源文件元数据（article 类型为 None）
    original_filename: str | None = None
    source_format: str | None = None  # md | txt | pdf | docx
    mime_type: str | None = None
    source_size: int | None = None
    chunk_count: int = 0
    channel_id: str | None = None
    channel_slug: str | None = None
    channel_name: str | None = None
    status: str = "pending"
    error_msg: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UploadFailedItem(BaseModel):
    """多文件上传中单个失败文件。"""

    filename: str
    reason: str


class UploadResult(BaseModel):
    """多文件上传结果。"""

    created: list[KnowledgeDocOut]
    failed: list[UploadFailedItem]


class DeleteResult(BaseModel):
    """删除文档结果。"""

    id: str
    deleted: bool = True


class ReindexResult(BaseModel):
    """单文档重建结果（异步任务派发响应）。"""

    doc_id: str
    task_id: str
    status: str = "queued"  # queued（已派发到 Celery）


class RebuildResult(BaseModel):
    """全量重建结果（异步任务派发响应）。"""

    task_id: str
    status: str = "queued"
