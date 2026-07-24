"""知识库后台路由：目录树、笔记 CRUD（含双链同步）、模板、反链。

笔记与文章共用 posts 表，此路由提供"知识库视角"的 API：
- 按 category/folder_path 组织目录树
- 新建/更新笔记时解析 [[双链]] 写入 note_links，并回填悬空链接
- 发布笔记（status=published）触发 RAG 入库（复用 posts 逻辑）
"""
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.crud.note_template import note_template as tpl_crud
from app.crud import note_link as note_link_crud
from app.crud.post import post as post_crud
from app.deps import AdminId, DBSession
from app.models.note_link import NoteLink
from app.models.post import Post
from app.schemas.common import Page, envelope
from app.schemas.note import (
    NoteDTO,
    NoteListItem,
    NoteLinkDTO,
    NoteTemplateCreate,
    NoteTemplateDTO,
    NoteTreeNode,
)
from app.schemas.post import PostCreate, PostUpdate
from app.services.cms import _paths_for_post, _tags_for_post, notify_revalidate
from app.services.note_tree import build_tree
from app.services.post_derive import (
    calculate_reading_time,
    derive_slug,
    generate_excerpt,
    generate_toc,
)

# 复用 posts 路由的入库派发逻辑（下划线私有，K2 暂复用，后续可抽到 service）
from app.api.admin.posts import (
    _apply_derived_fields,
    _try_dispatch_ingest_delete,
    _try_dispatch_ingest_publish,
    _try_sync_meili_delete,
    _try_sync_meili_upsert,
)

router = APIRouter(prefix="/kb")
logger = get_logger("admin.kb")


def _to_note(p: Post) -> NoteDTO:
    """ORM Post → NoteDTO。"""
    return NoteDTO(
        id=str(p.id),
        slug=p.slug,
        title=p.title,
        excerpt=p.excerpt,
        content_md=p.content_md,
        category=p.category,
        folder_path=p.folder_path,
        is_moc=p.is_moc,
        source_url=p.source_url,
        owner_id=str(p.owner_id) if p.owner_id else None,
        channel_id=str(p.channel_id) if p.channel_id else None,
        channel_slug=p.channel.slug if p.channel else None,
        channel_name=p.channel.name if p.channel else None,
        tags=p.tags or [],
        status=p.status,
        published_at=p.published_at.isoformat() if p.published_at else None,
        reading_time=p.reading_time,
        created_at=p.created_at.isoformat() if p.created_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
    )


def _to_list_item(p: Post) -> NoteListItem:
    """ORM Post → NoteListItem（轻量，不含正文）。"""
    return NoteListItem(
        id=str(p.id),
        slug=p.slug,
        title=p.title,
        excerpt=p.excerpt,
        category=p.category,
        folder_path=p.folder_path,
        is_moc=p.is_moc,
        tags=p.tags or [],
        status=p.status,
        published_at=p.published_at.isoformat() if p.published_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
    )


def _to_link_dto(link: NoteLink, *, source_title: str | None = None) -> NoteLinkDTO:
    """NoteLink → NoteLinkDTO。"""
    return NoteLinkDTO(
        id=str(link.id),
        target_note_id=str(link.target_note_id) if link.target_note_id else None,
        target_title_raw=link.target_title_raw,
        source_note_id=str(link.source_note_id) if link.source_note_id else None,
        source_title=source_title,
    )


def _to_template_dto(t) -> NoteTemplateDTO:
    """NoteTemplate → NoteTemplateDTO（手动转 UUID/datetime 为字符串）。"""
    return NoteTemplateDTO(
        id=str(t.id),
        name=t.name,
        category=t.category,
        description=t.description,
        content_md=t.content_md,
        created_at=t.created_at.isoformat() if t.created_at else None,
        updated_at=t.updated_at.isoformat() if t.updated_at else None,
    )


# ---------------- 目录树 ----------------


@router.get("/tree")
async def get_tree(db: DBSession, _: AdminId) -> dict:
    """知识库目录树（7 个 category + folder 子目录 + 笔记计数）。"""
    nodes = await build_tree(db)
    return envelope([n.model_dump() for n in nodes])


# ---------------- 笔记列表 ----------------


@router.get("/notes")
async def list_notes(
    db: DBSession,
    _: AdminId,
    category: str | None = Query(None),
    folder_path: str | None = Query(None),
    tag: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> dict:
    """笔记列表（知识库视角，含所有状态）。

    - category 精确匹配
    - folder_path 精确匹配；传 "null" 字符串表示该 category 下无子目录的笔记
    - tag 标签命中
    - q title/excerpt 模糊匹配
    """
    offset = (page - 1) * size
    stmt = select(Post).options(selectinload(Post.channel))
    count_stmt = select(func.count()).select_from(Post)

    if category:
        stmt = stmt.where(Post.category == category)
        count_stmt = count_stmt.where(Post.category == category)
    if folder_path is not None:
        if folder_path == "null":
            stmt = stmt.where(Post.folder_path.is_(None))
            count_stmt = count_stmt.where(Post.folder_path.is_(None))
        else:
            stmt = stmt.where(Post.folder_path == folder_path)
            count_stmt = count_stmt.where(Post.folder_path == folder_path)
    if tag:
        stmt = stmt.where(Post.tags.any(tag))  # type: ignore[attr-defined]
        count_stmt = count_stmt.where(Post.tags.any(tag))  # type: ignore[attr-defined]
    if q:
        like = f"%{q}%"
        cond = or_(Post.title.ilike(like), Post.excerpt.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    stmt = stmt.order_by(Post.updated_at.desc()).offset(offset).limit(size)
    items = list((await db.execute(stmt)).scalars().unique().all())
    total = (await db.execute(count_stmt)).scalar_one()

    page_obj = Page[NoteListItem](
        items=[_to_list_item(p) for p in items],
        total=total, page=page, size=size,
    )
    return envelope(page_obj.model_dump())


# ---------------- 笔记 CRUD ----------------


@router.post("/notes")
async def create_note(
    payload: PostCreate,
    db: DBSession,
    admin: AdminId,
) -> dict:
    """新建笔记。

    - channel_id 可空（私有笔记无频道）
    - category 默认 inbox
    - 保存后解析 [[双链]] 写入 note_links，并回填指向该标题的悬空链接
    - 若 status=published 则触发 RAG 入库
    """
    _apply_derived_fields(payload)
    existing = await post_crud.get_by_slug(db, payload.slug)
    if existing:
        raise ConflictError("slug 已存在")
    p = await post_crud.create(db, payload)
    # 双链同步
    await note_link_crud.sync_links(db, p.id, p.content_md)
    await note_link_crud.resolve_dangling_links(db, p.id, p.title)
    await db.commit()
    p = await post_crud.get_with_channel(db, p.id)
    logger.info("note_created", note_id=str(p.id), category=p.category, slug=p.slug)

    if p.status == "published":
        await notify_revalidate(
            paths=_paths_for_post(p.slug), tags=_tags_for_post(p.slug),
        )
        _try_dispatch_ingest_publish(str(p.id))
        await _try_sync_meili_upsert(p)
    return envelope(_to_note(p).model_dump())


@router.get("/notes/{note_id}")
async def get_note(db: DBSession, _: AdminId, note_id: UUID) -> dict:
    """笔记详情（含出链列表）。"""
    p = await post_crud.get_with_channel(db, note_id)
    if not p:
        raise NotFoundError("笔记不存在")
    outlinks = await note_link_crud.list_outgoing(db, note_id)
    return envelope({
        **_to_note(p).model_dump(),
        "outlinks": [_to_link_dto(l) for l in outlinks],
    })


@router.patch("/notes/{note_id}")
async def update_note(
    db: DBSession,
    _: AdminId,
    note_id: UUID,
    payload: PostUpdate,
) -> dict:
    """更新笔记。

    - 内容变更（content_md/title）时重建双链、回填悬空链接
    - 标题变更时回填指向新标题的悬空链接
    - published 且内容变更 → 重新入库
    - 从 published 切出 → 清理 chunks
    """
    p = await post_crud.get_with_channel(db, note_id)
    if not p:
        raise NotFoundError("笔记不存在")
    prev_status = p.status
    _apply_derived_fields(payload)

    if payload.slug and payload.slug != p.slug:
        existing = await post_crud.get_by_slug(db, payload.slug)
        if existing and existing.id != p.id:
            raise ConflictError("slug 已存在")

    p = await post_crud.update(db, p, payload)

    # 内容或标题变更 → 重建双链
    content_changed = any(
        f in payload.__pydantic_fields_set__ for f in ("content_md", "title")
    )
    if content_changed:
        await note_link_crud.sync_links(db, p.id, p.content_md)
        await note_link_crud.resolve_dangling_links(db, p.id, p.title)

    await db.commit()
    p = await post_crud.get_with_channel(db, p.id)
    logger.info("note_updated", note_id=str(p.id))

    # RAG 入库触发（与 posts 一致）
    rag_changed = any(
        f in payload.__pydantic_fields_set__
        for f in ("content_md", "title", "tags")
    )
    if p.status == "published" and rag_changed:
        _try_dispatch_ingest_publish(str(p.id))
        await _try_sync_meili_upsert(p)
    elif prev_status == "published" and p.status != "published":
        _try_dispatch_ingest_delete(str(p.id))
        await _try_sync_meili_delete(str(p.id))

    await notify_revalidate(
        paths=_paths_for_post(p.slug), tags=_tags_for_post(p.slug),
    )
    return envelope(_to_note(p).model_dump())


@router.delete("/notes/{note_id}")
async def delete_note(db: DBSession, _: AdminId, note_id: UUID) -> dict:
    """删除笔记（note_links 由外键 CASCADE 自动清理）。"""
    p = await post_crud.get(db, note_id)
    if not p:
        raise NotFoundError("笔记不存在")
    slug = p.slug
    was_published = p.status == "published"
    await post_crud.remove(db, p)
    await db.commit()
    if was_published:
        _try_dispatch_ingest_delete(str(note_id))
        await _try_sync_meili_delete(str(note_id))
    logger.info("note_deleted", note_id=str(note_id))
    await notify_revalidate(paths=_paths_for_post(slug), tags=_tags_for_post(slug))
    return envelope({"ok": True})


# ---------------- 反链 ----------------


@router.get("/notes/{note_id}/backlinks")
async def get_backlinks(db: DBSession, _: AdminId, note_id: UUID) -> dict:
    """反链面板：列出引用该笔记的所有笔记。"""
    p = await post_crud.get(db, note_id)
    if not p:
        raise NotFoundError("笔记不存在")
    rows = await note_link_crud.list_backlinks(db, note_id)
    items = [
        _to_link_dto(link, source_title=src.title).model_dump()
        for link, src in rows
    ]
    return envelope(items)


# ---------------- 模板 ----------------


@router.get("/templates")
async def list_templates(
    db: DBSession,
    _: AdminId,
    category: str | None = Query(None),
) -> dict:
    """模板列表（含系统内置 + 当前笔者自定义）。"""
    items = await tpl_crud.list_by_owner(db, category=category)
    return envelope([_to_template_dto(t).model_dump() for t in items])


@router.post("/templates")
async def create_template(
    payload: NoteTemplateCreate,
    db: DBSession,
    admin: AdminId,
) -> dict:
    """新建模板（归属当前笔者）。NoteTemplateCreate 不含 owner_id，create 后单独设。"""
    t = await tpl_crud.create(db, payload)
    t.owner_id = admin  # type: ignore[assignment]  # str → UUID 列自动转换
    await db.commit()
    logger.info("template_created", template_id=str(t.id), name=t.name)
    return envelope(_to_template_dto(t).model_dump())
