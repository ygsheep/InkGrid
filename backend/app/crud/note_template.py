"""笔记模板 CRUD。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.note_template import NoteTemplate
from app.schemas.note import NoteTemplateCreate


class CRUDNoteTemplate(CRUDBase[NoteTemplate, NoteTemplateCreate, NoteTemplateCreate]):
    """模板数据访问层。"""

    async def list_by_owner(
        self,
        db: AsyncSession,
        *,
        owner_id: UUID | None = None,
        category: str | None = None,
    ) -> list[NoteTemplate]:
        """按归属与分类列出模板。

        owner_id 为 None 时返回系统内置模板（owner_id IS NULL）。
        """
        stmt = select(NoteTemplate)
        if owner_id is not None:
            stmt = stmt.where(
                (NoteTemplate.owner_id == owner_id)
                | (NoteTemplate.owner_id.is_(None))
            )
        else:
            stmt = stmt.where(NoteTemplate.owner_id.is_(None))
        if category:
            stmt = stmt.where(NoteTemplate.category == category)
        stmt = stmt.order_by(NoteTemplate.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())


note_template = CRUDNoteTemplate(NoteTemplate)
