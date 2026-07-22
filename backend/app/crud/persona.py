"""人设 CRUD。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate


class CRUDPersona(CRUDBase[Persona, PersonaCreate, PersonaUpdate]):
    """人设数据访问层。"""

    async def get_by_serial(self, db: AsyncSession, serial: str) -> Persona | None:
        """按 serial 取人设。"""
        stmt = select(Persona).where(Persona.serial == serial)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        db: AsyncSession,
        *,
        scope: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Persona], int]:
        """人设列表（按 created_at asc）。"""
        stmt = select(Persona)
        count_stmt = select(func.count()).select_from(Persona)
        if scope:
            stmt = stmt.where(Persona.scope == scope)
            count_stmt = count_stmt.where(Persona.scope == scope)
        stmt = stmt.order_by(Persona.created_at.asc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())
        total = (await db.execute(count_stmt)).scalar_one()
        return items, total


persona = CRUDPersona(Persona)
