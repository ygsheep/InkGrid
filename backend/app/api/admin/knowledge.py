"""后台知识库路由。

对应后端设计 §5.3：
- GET    /admin/knowledge/docs              文档列表（含入库状态）
- GET    /admin/knowledge/docs/:id          文档详情
- POST   /admin/knowledge/upload            多文件多格式上传（md/txt/pdf/docx）
- GET    /admin/knowledge/docs/:id/download 下载源文件（从 MinIO 流式返回）
- DELETE /admin/knowledge/docs/:id          删除文档（chunks + Milvus + MinIO 源文件）
- POST   /admin/knowledge/docs/:id/reindex  重建单文档向量（异步）
- POST   /admin/knowledge/rebuild           全量重建（异步）

设计要点：
- 上传文档与文章共用 KnowledgeDoc 表，source_type=upload
- 多文件上传：逐文件校验 → 归档 MinIO → 解析入库，失败文件进 failed 列表不阻断其他文件
- reindex / rebuild 派发到 Celery worker 执行（避免阻塞 HTTP 请求）
- Milvus 写入失败不阻断入库（status=partial），符合"RAG 失败不能让博客宕机"
"""
import re
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.errors import AppError, NotFoundError
from app.core.logging import get_logger
from app.crud.knowledge import knowledge as knowledge_crud
from app.deps import AdminId, DBSession
from app.ingest.pipeline import ingest_upload, remove_upload_doc
from app.schemas.common import envelope
from app.services import storage
from app.services.upload_security import (
    UploadSecurityError,
    validate_document_file,
)

router = APIRouter(prefix="/knowledge")
logger = get_logger("admin.knowledge")


def _to_dict(doc) -> dict:
    """ORM KnowledgeDoc → dict（含 channel 摘要与源文件元数据）。"""
    ch = doc.channel if doc.channel is not None else None
    return {
        "id": str(doc.id),
        "source_type": doc.source_type,
        "source_id": str(doc.source_id) if doc.source_id else None,
        "title": doc.title,
        "raw_uri": doc.raw_uri,
        "original_filename": doc.original_filename,
        "source_format": doc.source_format,
        "mime_type": doc.mime_type,
        "source_size": doc.source_size,
        "chunk_count": doc.chunk_count,
        "channel_id": str(doc.channel_id) if doc.channel_id else None,
        "channel_slug": ch.slug if ch else None,
        "channel_name": ch.name if ch else None,
        "status": doc.status,
        "error_msg": doc.error_msg,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _extract_title(validated, explicit_title: str | None) -> str:
    """提取文档标题：参数优先 > md 首个 # 标题 > 文件名去扩展名。"""
    if explicit_title:
        return explicit_title.strip()
    # md 尝试从内容首 # 提取
    if validated.source_format == "md" and validated.text:
        for line in validated.text.splitlines():
            m = re.match(r"^#\s+(.+?)\s*$", line)
            if m:
                return m.group(1).strip()
    # 兜底：文件名去扩展名
    base = validated.filename
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return base.strip() or "untitled"


@router.get("/docs")
async def list_docs(
    db: DBSession,
    _: AdminId,
    source_type: str | None = Query(None, description="article | upload | policy"),
    status: str | None = Query(None, description="pending | indexed | partial | failed"),
    channel_id: UUID | None = Query(None),
    q: str | None = Query(None, description="标题模糊匹配"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """知识库文档列表（含入库状态、频道信息、源文件元数据）。"""
    offset = (page - 1) * size
    items, total = await knowledge_crud.list_docs(
        db,
        source_type=source_type,
        status=status,
        channel_id=channel_id,
        q=q,
        offset=offset,
        limit=size,
    )
    return envelope({
        "items": [_to_dict(d) for d in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.get("/docs/{doc_id}")
async def get_doc(
    db: DBSession,
    _: AdminId,
    doc_id: UUID,
) -> dict:
    """知识库文档详情。"""
    doc = await knowledge_crud.get_with_channel(db, doc_id)
    if not doc:
        raise NotFoundError("文档不存在")
    return envelope(_to_dict(doc))


@router.post("/upload")
async def upload_docs(
    db: DBSession,
    _: AdminId,
    files: list[UploadFile] = File(..., description="多文件（md/txt/pdf/docx）"),
    channel_id: UUID = Form(..., description="归属频道 ID"),
    title: str | None = Form(
        None, description="可选标题（仅单文件时生效，多文件按文件名/内容提取）"
    ),
) -> dict:
    """多文件多格式上传到知识库（source_type=upload）。

    每个文件独立处理：
    1. 安全校验（validate_document_file：扩展名/MIME/分级大小/编码/magic bytes）
    2. 归档源文件到 MinIO（硬失败 → 进 failed 列表）
    3. 按 source_format 解析 → 分块 → 写 PG → embedding → 写 Milvus
    4. 收集结果：created（含 status=indexed/partial/failed）+ failed（校验/归档失败）

    单次最多 20 个文件（前端限制，后端不强制，靠网关/前端约束）。
    """
    if not files:
        raise AppError("未提供文件", status_code=400, code=4000)

    # 循环里只收集 doc_id，避免在 commit 前访问 doc.channel 触发 lazy load
    # （异步 session 的 lazy load 需 greenlet，会抛 MissingGreenlet）
    created_ids: list[UUID] = []
    failed: list[dict] = []

    # 多文件时 title 参数忽略，逐文件从内容/文件名提取
    explicit_title = title if len(files) == 1 else None

    for file in files:
        filename = file.filename or "untitled"
        # 1. 安全校验
        try:
            validated = validate_document_file(file)
        except UploadSecurityError as e:
            failed.append({"filename": filename, "reason": str(e)})
            continue

        title_val = _extract_title(validated, explicit_title)

        # 2-3. 归档 + 入库（硬失败进 failed，解析失败返回 status=failed 的 doc 进 created）
        try:
            doc = await ingest_upload(
                db,
                title=title_val,
                channel_id=channel_id,
                validated=validated,
            )
        except ValueError as e:
            # channel 不存在等业务错误（所有文件共用，直接中断）
            raise AppError(str(e), status_code=400, code=4000) from e
        except Exception as e:
            # MinIO 归档失败等硬失败，单个文件失败不阻断其他
            logger.warning(
                "knowledge_upload_failed",
                filename=filename,
                error=str(e),
            )
            failed.append({"filename": filename, "reason": f"归档/入库失败: {e}"})
            continue

        created_ids.append(doc.id)

    # 统一提交：成功与解析失败的 doc 一并持久化（status=failed 的也入库便于重建）
    await db.commit()

    # commit 后统一通过 get_with_channel（selectinload 预加载 channel）重新加载，
    # 避免 _to_dict 访问 doc.channel 时触发异步 lazy load
    reloaded: list[dict] = []
    for doc_id in created_ids:
        doc = await knowledge_crud.get_with_channel(db, doc_id)
        if doc:
            reloaded.append(_to_dict(doc))
        else:
            # 极端情况：commit 后查不到（已被并发删除），兜底返回 id
            logger.warning("knowledge_doc_missing_after_commit", doc_id=str(doc_id))
            reloaded.append({"id": str(doc_id), "status": "missing"})

    logger.info(
        "knowledge_batch_uploaded",
        channel_id=str(channel_id),
        created=len(reloaded),
        failed=len(failed),
    )
    return envelope({"created": reloaded, "failed": failed})


@router.get("/docs/{doc_id}/download")
async def download_doc(
    db: DBSession,
    _: AdminId,
    doc_id: UUID,
) -> StreamingResponse:
    """下载知识库源文件（从 MinIO 流式返回，还原文件名）。

    仅 upload 类型且有 raw_uri（MinIO 归档）的文档可下载。
    Content-Disposition 用 original_filename 还原下载文件名。
    """
    doc = await knowledge_crud.get(db, doc_id)
    if not doc:
        raise NotFoundError("文档不存在")
    if doc.source_type != "upload" or not doc.raw_uri:
        raise AppError(
            "该文档无源文件可下载（文章类型或未归档）",
            status_code=400,
            code=4000,
        )

    try:
        resp = storage.get_object(doc.raw_uri)
    except Exception as e:
        logger.warning("minio_get_failed", doc_id=str(doc_id), error=str(e))
        raise AppError(f"源文件获取失败: {e}", status_code=500, code=5000) from e

    # 还原下载文件名（original_filename 优先，兜底 raw_uri 末段）
    download_name = doc.original_filename or doc.raw_uri.rsplit("/", 1)[-1]
    content_type = doc.mime_type or "application/octet-stream"

    return StreamingResponse(
        resp.stream(64 * 1024),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
        },
    )


@router.delete("/docs/{doc_id}")
async def delete_doc(
    db: DBSession,
    _: AdminId,
    doc_id: UUID,
) -> dict:
    """删除知识库文档（chunks + Milvus 向量 + MinIO 源文件）。

    - upload 类型：清理 MinIO 源文件 + Milvus 向量 + chunks + doc
    - article 类型：拒绝（文章入库/删除由文章 CRUD 驱动，不可在此删）
    """
    doc = await knowledge_crud.get(db, doc_id)
    if not doc:
        raise NotFoundError("文档不存在")
    if doc.source_type == "article":
        raise AppError(
            "文章类型文档不可直接删除，请通过文章删除/下架操作",
            status_code=400,
            code=4000,
        )

    await remove_upload_doc(db, doc)
    await db.commit()

    logger.info("knowledge_doc_deleted", doc_id=str(doc_id), title=doc.title)
    return envelope({"id": str(doc_id), "deleted": True})


@router.post("/docs/{doc_id}/reindex")
async def reindex_doc(
    db: DBSession,
    _: AdminId,
    doc_id: UUID,
) -> dict:
    """重建单个文档的向量（异步 Celery 任务）。

    根据 source_type 分派：
    - article: 重新加载 post 内容走 ingest_article（删旧建新）
    - upload: 基于已有 parsed_text 重新分块 + 写 Milvus；parsed_text 空则从 MinIO 重解析
    - policy: P1 阶段实现
    """
    doc = await knowledge_crud.get(db, doc_id)
    if not doc:
        raise NotFoundError("文档不存在")

    try:
        from app.tasks.reindex_tasks import reindex_doc_task

        task = reindex_doc_task.delay(str(doc_id))
    except Exception as e:
        logger.warning("reindex_dispatch_failed", doc_id=str(doc_id), error=str(e))
        raise AppError(
            f"重建任务派发失败: {e}", status_code=500, code=5000
        ) from e

    logger.info(
        "reindex_dispatched",
        doc_id=str(doc_id),
        task_id=task.id,
        source_type=doc.source_type,
    )
    return envelope({
        "doc_id": str(doc_id),
        "task_id": task.id,
        "status": "queued",
    })


@router.post("/rebuild")
async def rebuild_all(
    _: AdminId,
) -> dict:
    """全量重建知识库（异步 Celery 任务，慎用）。

    遍历所有已发布文章，删旧 chunks + 重新入库。
    设计 §7.4 的"临时 collection + alias 切换"为 P4 目标，
    P0+ 阶段简化为顺序重建（适合文章数 < 1000 的场景）。
    """
    try:
        from app.tasks.reindex_tasks import rebuild_all_task

        task = rebuild_all_task.delay()
    except Exception as e:
        logger.warning("rebuild_dispatch_failed", error=str(e))
        raise AppError(
            f"全量重建任务派发失败: {e}", status_code=500, code=5000
        ) from e

    logger.info("rebuild_dispatched", task_id=task.id)
    return envelope({"task_id": task.id, "status": "queued"})
