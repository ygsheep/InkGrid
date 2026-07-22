"""入库任务：on_post_publish / on_post_update / on_post_delete。

在 Celery worker 中执行（同步入口，内部用 asyncio.run 跑异步 pipeline）。
"""
import asyncio
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.ingest.pipeline import ingest_article, remove_article_chunks
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.ingest")


@celery_app.task(name="ingest.on_post_publish", bind=True, max_retries=3)
def on_post_publish(self, post_id: str) -> dict:
    """文章发布/更新入库。

    P0 阶段：解析 → 分块 → 写 PG chunks（不含 Embedding）。
    P1 阶段：在 pipeline 后追加 embed + milvus write。
    """
    configure_logging()
    pid = UUID(str(post_id))
    try:
        return asyncio.run(_run_ingest(pid))
    except Exception as e:
        logger.exception("ingest_task_failed", post_id=post_id, error=str(e))
        # 重试：指数退避
        raise self.retry(exc=e, countdown=2 ** min(self.request.retries, 5))


async def _run_ingest(post_id: UUID) -> dict:
    """实际入库逻辑（异步）。"""
    async with async_session_factory() as db:
        doc = await ingest_article(db, post_id)
        await db.commit()
    return {
        "doc_id": str(doc.id),
        "status": doc.status,
        "chunk_count": doc.chunk_count,
    }


@celery_app.task(name="ingest.on_post_delete")
def on_post_delete(post_id: str) -> dict:
    """文章删除/下架：清理 chunks + knowledge_doc。"""
    configure_logging()
    pid = UUID(str(post_id))
    return asyncio.run(_run_remove(pid))


async def _run_remove(post_id: UUID) -> dict:
    """实际清理逻辑（异步）。"""
    async with async_session_factory() as db:
        removed = await remove_article_chunks(db, post_id)
        await db.commit()
    return {"removed_docs": removed}
