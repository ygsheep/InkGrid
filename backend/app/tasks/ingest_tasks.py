"""入库任务：on_post_publish / on_post_update / on_post_delete。

在 Celery worker 中执行（同步入口，内部用 asyncio.run 跑异步 pipeline）。
入库成功后异步触发 Q&A 生成任务。
"""
import asyncio
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.crud import qa as qa_crud
from app.db.session import async_session_factory
from app.ingest.pipeline import ingest_article, remove_article_chunks
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.ingest")


@celery_app.task(name="ingest.on_post_publish", bind=True, max_retries=3)
def on_post_publish(self, post_id: str) -> dict:
    """文章发布/更新入库 + 触发 Q&A 生成。"""
    configure_logging()
    pid = UUID(str(post_id))
    try:
        result = asyncio.run(_run_ingest(pid))
        # 入库成功后异步触发 Q&A 生成
        from app.tasks.qa_tasks import generate_qa
        generate_qa.delay(post_id)
        return result
    except Exception as e:
        logger.exception("ingest_task_failed", post_id=post_id, error=str(e))
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
    """文章删除/下架：清理 chunks + knowledge_doc + Q&A。"""
    configure_logging()
    pid = UUID(str(post_id))
    return asyncio.run(_run_remove(pid))


async def _run_remove(post_id: UUID) -> dict:
    """实际清理逻辑（异步）。"""
    async with async_session_factory() as db:
        removed = await remove_article_chunks(db, post_id)
        # 同时清理 Q&A 对
        qa_deleted = await qa_crud.delete_by_article(db, post_id)
        await db.commit()
    return {"removed_docs": removed, "removed_qa": qa_deleted}
