"""知识库文档 CRUD。

列表查询支持按 source_type / status / channel_id / 关键字筛选，
返回时通过 selectinload 预加载 channel 关系，避免 N+1。

创建/更新不在本层提供：article 由 ingest_article 内部创建，
upload 文档由 ingest_upload 创建，reindex 不修改主键。
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.knowledge import KnowledgeDoc


class CRUDKnowledge(CRUDBase[KnowledgeDoc, dict, dict]):
    """知识库文档数据访问层。

    泛型入参用 dict 占位：本项目没有 schema 形式的 create/update 入参，
    知识库文档的写入全部由 ingest pipeline 内部完成（直接构造 ORM）。
    """

    async def list_docs(
        self,
        db: AsyncSession,
        *,
        source_type: str | None = None,
        status: str | None = None,
        channel_id: UUID | None = None,
        q: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[KnowledgeDoc], int]:
        """知识库文档列表（含 channel 关联）。

        - source_type: article | upload | policy
        - status: pending | indexed | partial | failed
        - channel_id: 频道 ID 精确匹配
        - q: title 模糊匹配
        返回 (items, total)，按 created_at desc。
        """
        stmt = select(KnowledgeDoc).options(selectinload(KnowledgeDoc.channel))
        count_stmt = select(func.count()).select_from(KnowledgeDoc)

        if source_type:
            stmt = stmt.where(KnowledgeDoc.source_type == source_type)
            count_stmt = count_stmt.where(KnowledgeDoc.source_type == source_type)
        if status:
            stmt = stmt.where(KnowledgeDoc.status == status)
            count_stmt = count_stmt.where(KnowledgeDoc.status == status)
        if channel_id:
            stmt = stmt.where(KnowledgeDoc.channel_id == channel_id)
            count_stmt = count_stmt.where(KnowledgeDoc.channel_id == channel_id)
        if q:
            like = f"%{q}%"
            cond = KnowledgeDoc.title.ilike(like)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(KnowledgeDoc.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())
        total = (await db.execute(count_stmt)).scalar_one()
        return items, total

    async def get_with_channel(
        self,
        db: AsyncSession,
        doc_id: UUID,
    ) -> KnowledgeDoc | None:
        """按 id 取文档（含 channel 预加载）。用于 admin 详情。"""
        stmt = (
            select(KnowledgeDoc)
            .options(selectinload(KnowledgeDoc.channel))
            .where(KnowledgeDoc.id == doc_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


knowledge = CRUDKnowledge(KnowledgeDoc)
