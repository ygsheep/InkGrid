"""公开人设路由：GET /api/personas（不含 system_prompt）。"""
from fastapi import APIRouter, Query

from app.crud.persona import persona as persona_crud
from app.deps import DBSession
from app.schemas.common import Page, envelope
from app.schemas.persona import Persona

router = APIRouter()


def _to_persona(p) -> Persona:
    """ORM Persona → Persona schema（不含 system_prompt）。"""
    return Persona(
        id=str(p.id),
        serial=p.serial,
        name=p.name,
        tagline=p.tagline,
        description=p.description,
        tags=p.tags or [],
        avatar=p.avatar,
    )


@router.get("/personas")
async def list_personas(
    db: DBSession,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> dict:
    """公开人设列表。"""
    offset = (page - 1) * size
    items, total = await persona_crud.list_all(db, offset=offset, limit=size)
    page_obj = Page[Persona](
        items=[_to_persona(p) for p in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())
