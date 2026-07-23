"""后台人设路由：GET/POST/PATCH/DELETE /admin/personas[/:id]。"""
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.crud.persona import persona as persona_crud
from app.deps import AdminId, DBSession
from app.schemas.common import Page, envelope
from app.schemas.persona import PersonaAdmin, PersonaCreate, PersonaUpdate

router = APIRouter(prefix="/personas")
logger = get_logger("admin.personas")


def _to_admin(p) -> PersonaAdmin:
    """ORM Persona → PersonaAdmin（含 system_prompt / scope）。"""
    return PersonaAdmin(
        id=str(p.id),
        serial=p.serial,
        name=p.name,
        tagline=p.tagline,
        description=p.description,
        tags=p.tags or [],
        avatar=p.avatar,
        system_prompt=p.system_prompt,
        scope=p.scope,
    )


@router.get("")
async def list_personas(
    db: DBSession,
    _: AdminId,
    scope: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> dict:
    """人设列表（含 system_prompt）。"""
    offset = (page - 1) * size
    items, total = await persona_crud.list_all(
        db, scope=scope, offset=offset, limit=size
    )
    page_obj = Page[PersonaAdmin](
        items=[_to_admin(p) for p in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())


@router.post("")
async def create_persona(
    payload: PersonaCreate,
    db: DBSession,
    _: AdminId,
) -> dict:
    """新建人设。"""
    existing = await persona_crud.get_by_serial(db, payload.serial)
    if existing:
        raise ConflictError("serial 已存在")
    p = await persona_crud.create(db, payload)
    await db.commit()
    logger.info("persona_created", persona_id=str(p.id), serial=p.serial)
    return envelope(_to_admin(p).model_dump())


@router.get("/{persona_id}")
async def get_persona(db: DBSession, _: AdminId, persona_id: UUID) -> dict:
    """人设详情。"""
    p = await persona_crud.get(db, persona_id)
    if not p:
        raise NotFoundError("人设不存在")
    return envelope(_to_admin(p).model_dump())


@router.patch("/{persona_id}")
async def update_persona(
    db: DBSession,
    _: AdminId,
    persona_id: UUID,
    payload: PersonaUpdate,
) -> dict:
    """更新人设。"""
    p = await persona_crud.get(db, persona_id)
    if not p:
        raise NotFoundError("人设不存在")
    if payload.serial and payload.serial != p.serial:
        existing = await persona_crud.get_by_serial(db, payload.serial)
        if existing and existing.id != p.id:
            raise ConflictError("serial 已存在")
    p = await persona_crud.update(db, p, payload)
    await db.commit()
    logger.info("persona_updated", persona_id=str(p.id))
    return envelope(_to_admin(p).model_dump())


@router.delete("/{persona_id}")
async def delete_persona(db: DBSession, _: AdminId, persona_id: UUID) -> dict:
    """删除人设。

    关联的 Channel.persona_id FK 为 ondelete=SET NULL，会自动置空。
    """
    p = await persona_crud.get(db, persona_id)
    if not p:
        raise NotFoundError("人设不存在")
    await persona_crud.remove(db, p)
    await db.commit()
    logger.info("persona_deleted", persona_id=str(persona_id))
    return envelope({"ok": True})
