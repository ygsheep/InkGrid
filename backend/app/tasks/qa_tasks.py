"""Q&A 生成任务：文章发布后异步生成 Q&A 对。

在 Celery worker 中执行（同步入口，内部用 asyncio.run 跑异步逻辑）。
"""
import asyncio
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.services.qa.generator import generate_qa_for_article
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.qa")


@celery_app.task(name="qa.generate_for_article", bind=True, max_retries=3)
def generate_qa(self, post_id: str) -> dict:
    """文章发布后异步生成 Q&A 对，写入 PG (status=pending)。"""
    configure_logging()
    pid = UUID(str(post_id))
    try:
        return asyncio.run(_run_generate(pid))
    except Exception as e:
        logger.exception("qa_task_failed", post_id=post_id, error=str(e))
        raise self.retry(exc=e, countdown=2 ** min(self.request.retries, 5))


async def _run_generate(post_id: UUID) -> dict:
    """实际生成逻辑（异步）。"""
    async with async_session_factory() as db:
        count = await generate_qa_for_article(db, post_id)
        await db.commit()
    return {"post_id": str(post_id), "qa_count": count}
