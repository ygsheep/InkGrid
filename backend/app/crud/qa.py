"""QaPair CRUD：按文章列出/创建/审核/删除。"""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.qa_pair import QaPair


async def list_by_article(
    db: AsyncSession, article_id: UUID, status: str | None = None,
) -> list[QaPair]:
    """列出文章下的 Q&A，可选按状态过滤。"""
    stmt = select(QaPair).where(QaPair.article_id == article_id)
    if status:
        stmt = stmt.where(QaPair.status == status)
    stmt = stmt.order_by(QaPair.created_at)
    return list((await db.execute(stmt)).scalars().all())


async def list_pending(db: AsyncSession, offset: int = 0, limit: int = 50) -> list[QaPair]:
    """列出待审核 Q&A（含文章信息）。"""
    stmt = (
        select(QaPair)
        .options(joinedload(QaPair.article))
        .where(QaPair.status == "pending")
        .order_by(QaPair.created_at)
        .offset(offset)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get(db: AsyncSession, qa_id: UUID) -> QaPair | None:
    """按主键取一条。"""
    return await db.get(QaPair, qa_id)


async def create(
    db: AsyncSession,
    *,
    article_id: UUID,
    question: str,
    answer: str,
    status: str = "pending",
) -> QaPair:
    """新建 Q&A。调用方负责 commit。"""
    qa = QaPair(
        article_id=article_id,
        question=question,
        answer=answer,
        status=status,
    )
    db.add(qa)
    await db.flush()
    await db.refresh(qa)
    return qa


async def update_status(
    db: AsyncSession, qa: QaPair, status: str, milvus_chunk_id: str | None = None,
) -> QaPair:
    """更新审核状态。调用方负责 commit。"""
    qa.status = status
    if milvus_chunk_id is not None:
        qa.milvus_chunk_id = milvus_chunk_id
    db.add(qa)
    await db.flush()
    return qa


async def delete_by_article(db: AsyncSession, article_id: UUID) -> int:
    """删除文章下所有 Q&A（文章删除时级联调用）。"""
    result = await db.execute(
        delete(QaPair).where(QaPair.article_id == article_id)
    )
    await db.flush()
    return result.rowcount


async def list_approved_by_article(db: AsyncSession, article_id: UUID) -> list[QaPair]:
    """列出文章下已审核通过的 Q&A。"""
    return await list_by_article(db, article_id, status="approved")
