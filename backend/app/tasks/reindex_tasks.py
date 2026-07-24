"""重建任务：单文档重建 + 全量重建。

在 Celery worker 中执行（同步入口，内部用 asyncio.run 跑异步 pipeline）。
对应后端设计 §5.3 的：
- POST /admin/knowledge/docs/:id/reindex  → reindex_doc_task
- POST /admin/knowledge/rebuild           → rebuild_all_task

设计 §7.4 的"临时 collection + alias 切换"为 P4 上云目标，
P0+ 阶段简化为顺序重建（适合文章数 < 1000 的场景）。
"""
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.ingest.pipeline import ingest_article, reindex_upload
from app.models.knowledge import KnowledgeDoc
from app.models.post import Post
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.reindex")


@celery_app.task(name="reindex.doc", bind=True, max_retries=2)
def reindex_doc_task(self, doc_id: str) -> dict:
    """重建单个文档向量。

    根据 source_type 走不同路径：
    - article: 重新加载 post 内容，走 ingest_article（删旧建新，幂等）
    - upload:  基于 parsed_text 重新分块 + 写 Milvus（reindex_upload）
    - policy:  P1 阶段实现
    """
    configure_logging()
    try:
        return asyncio.run(_run_reindex_doc(UUID(doc_id)))
    except Exception as e:
        logger.exception("reindex_doc_failed", doc_id=doc_id, error=str(e))
        # 重试：指数退避（最多 2 次）
        raise self.retry(exc=e, countdown=2 ** min(self.request.retries, 5))


async def _run_reindex_doc(doc_id: UUID) -> dict:
    """实际重建逻辑（异步）。"""
    async with async_session_factory() as db:
        doc = await db.get(KnowledgeDoc, doc_id)
        if not doc:
            return {"doc_id": str(doc_id), "status": "not_found"}

        if doc.source_type == "article" and doc.source_id:
            # 走文章入库管道（内部会删旧 doc + chunks + Milvus 向量，然后重建）
            doc = await ingest_article(db, doc.source_id)
            await db.commit()
            return {
                "doc_id": str(doc.id),
                "status": doc.status,
                "chunk_count": doc.chunk_count,
            }
        elif doc.source_type == "upload":
            # 上传文档：基于 parsed_text 重新分块 + 写 Milvus
            doc = await reindex_upload(db, doc)
            await db.commit()
            return {
                "doc_id": str(doc.id),
                "status": doc.status,
                "chunk_count": doc.chunk_count,
            }
        else:
            # policy 等其他类型：P1 阶段实现
            return {
                "doc_id": str(doc_id),
                "status": "unsupported_source_type",
                "source_type": doc.source_type,
            }


@celery_app.task(name="reindex.all")
def rebuild_all_task() -> dict:
    """全量重建：遍历所有已发布文章，删旧 + 重新入库。

    不加分布式锁（P0+ 单 worker 场景天然串行）；
    P4 上云时改为临时 collection + alias 切换 + 分布式锁。
    """
    configure_logging()
    return asyncio.run(_run_rebuild_all())


async def _run_rebuild_all() -> dict:
    """实际全量重建逻辑（异步，顺序执行）。"""
    async with async_session_factory() as db:
        # 查所有已发布文章 ID（按发布时间升序，便于日志追踪）
        stmt = (
            select(Post.id)
            .where(Post.status == "published")
            .order_by(Post.published_at.asc().nullslast())
        )
        post_ids = (await db.execute(stmt)).scalars().all()

        success = 0
        failed = 0
        for pid in post_ids:
            try:
                await ingest_article(db, pid)
                await db.commit()
                success += 1
            except Exception as e:
                await db.rollback()
                failed += 1
                logger.exception(
                    "rebuild_post_failed",
                    post_id=str(pid),
                    error=str(e),
                )

        logger.info(
            "rebuild_all_done",
            total=len(post_ids),
            success=success,
            failed=failed,
        )
        return {
            "total": len(post_ids),
            "success": success,
            "failed": failed,
        }
