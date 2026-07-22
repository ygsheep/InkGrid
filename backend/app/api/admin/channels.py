"""后台频道路由：GET/POST/PATCH/DELETE /admin/channels[/:id]。"""
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.crud.channel import channel as channel_crud
from app.deps import AdminId, DBSession
from app.schemas.channel import ChannelCreate, ChannelUpdate
from app.schemas.common import Page, envelope

router = APIRouter(prefix="/channels")
logger = get_logger("admin.channels")


def _to_dict(ch) -> dict:
    """ORM Channel → dict（含 persona_id / postCount）。"""
    return {
        "id": str(ch.id),
        "slug": ch.slug,
        "name": ch.name,
        "description": ch.description,
        "accent": ch.accent,
        "persona_id": str(ch.persona_id) if ch.persona_id else None,
        "postCount": len(ch.posts) if ch.posts is not None else 0,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
    }


@router.get("")
async def list_channels(
    db: DBSession,
    _: AdminId,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> dict:
    """频道列表。"""
    offset = (page - 1) * size
    items, total = await channel_crud.list_all(db, offset=offset, limit=size)
    return envelope({
        "items": [_to_dict(ch) for ch in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.post("")
async def create_channel(
    payload: ChannelCreate,
    db: DBSession,
    _: AdminId,
) -> dict:
    """新建频道。"""
    existing = await channel_crud.get_by_slug(db, payload.slug)
    if existing:
        raise ConflictError("slug 已存在")
    ch = await channel_crud.create(db, payload)
    await db.commit()
    logger.info("channel_created", channel_id=str(ch.id), slug=ch.slug)
    return envelope(_to_dict(ch))


@router.get("/{channel_id}")
async def get_channel(db: DBSession, _: AdminId, channel_id: UUID) -> dict:
    """频道详情。"""
    ch = await channel_crud.get(db, channel_id)
    if not ch:
        raise NotFoundError("频道不存在")
    return envelope(_to_dict(ch))


@router.patch("/{channel_id}")
async def update_channel(
    db: DBSession,
    _: AdminId,
    channel_id: UUID,
    payload: ChannelUpdate,
) -> dict:
    """更新频道。"""
    ch = await channel_crud.get(db, channel_id)
    if not ch:
        raise NotFoundError("频道不存在")
    if payload.slug and payload.slug != ch.slug:
        existing = await channel_crud.get_by_slug(db, payload.slug)
        if existing and existing.id != ch.id:
            raise ConflictError("slug 已存在")
    ch = await channel_crud.update(db, ch, payload)
    await db.commit()
    logger.info("channel_updated", channel_id=str(ch.id))
    return envelope(_to_dict(ch))


@router.delete("/{channel_id}")
async def delete_channel(db: DBSession, _: AdminId, channel_id: UUID) -> dict:
    """删除频道。

    注意：model 中 posts 关系 ondelete=RESTRICT，若频道下有文章会失败。
    """
    ch = await channel_crud.get(db, channel_id)
    if not ch:
        raise NotFoundError("频道不存在")
    await channel_crud.remove(db, ch)
    await db.commit()
    logger.info("channel_deleted", channel_id=str(channel_id))
    return envelope({"ok": True})
