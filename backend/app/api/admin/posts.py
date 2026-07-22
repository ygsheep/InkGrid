"""后台文章路由：GET/POST/PATCH/DELETE /admin/posts[/:id]、状态切换、revalidate。

发布（status=published）触发入库任务（P0-9 接入）。
"""
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.crud.post import post as post_crud
from app.deps import AdminId, DBSession
from app.schemas.common import Page, envelope
from app.schemas.post import (
    ArticleAdmin,
    PostCreate,
    PostStatusUpdate,
    PostUpdate,
)

router = APIRouter(prefix="/posts")
logger = get_logger("admin.posts")


def _to_admin(p) -> ArticleAdmin:
    """ORM Post → ArticleAdmin。"""
    return ArticleAdmin(
        id=str(p.id),
        slug=p.slug,
        title=p.title,
        excerpt=p.excerpt,
        content=p.content_md,
        html=p.content_html,
        channel_id=str(p.channel_id),
        channel_slug=p.channel.slug if p.channel else None,
        channel_name=p.channel.name if p.channel else None,
        tags=p.tags or [],
        status=p.status,
        published_at=p.published_at.isoformat() if p.published_at else None,
        reading_time=p.reading_time,
        toc=p.toc or [],
        created_at=p.created_at.isoformat() if p.created_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
    )


@router.get("")
async def list_posts(
    db: DBSession,
    _: AdminId,
    status: str | None = Query(None),
    channel_id: UUID | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """后台文章列表（含所有状态）。"""
    offset = (page - 1) * size
    items, total = await post_crud.list_admin(
        db,
        status=status,
        channel_id=channel_id,
        q=q,
        offset=offset,
        limit=size,
    )
    page_obj = Page[ArticleAdmin](
        items=[_to_admin(p) for p in items],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())


@router.post("")
async def create_post(
    payload: PostCreate,
    db: DBSession,
    _: AdminId,
) -> dict:
    """新建文章。"""
    # slug 唯一性预检
    existing = await post_crud.get_by_slug(db, payload.slug)
    if existing:
        raise ConflictError("slug 已存在")
    p = await post_crud.create(db, payload)
    await db.commit()
    # 重新加载 channel 关系（async session 不支持懒加载）
    p = await post_crud.get_with_channel(db, p.id)
    logger.info("post_created", post_id=str(p.id), slug=p.slug)
    return envelope(_to_admin(p).model_dump())


@router.get("/{post_id}")
async def get_post(db: DBSession, _: AdminId, post_id: UUID) -> dict:
    """文章详情。"""
    p = await post_crud.get_with_channel(db, post_id)
    if not p:
        raise NotFoundError("文章不存在")
    return envelope(_to_admin(p).model_dump())


@router.patch("/{post_id}")
async def update_post(
    db: DBSession,
    _: AdminId,
    post_id: UUID,
    payload: PostUpdate,
) -> dict:
    """更新文章。"""
    p = await post_crud.get_with_channel(db, post_id)
    if not p:
        raise NotFoundError("文章不存在")
    # slug 变更时预检
    if payload.slug and payload.slug != p.slug:
        existing = await post_crud.get_by_slug(db, payload.slug)
        if existing and existing.id != p.id:
            raise ConflictError("slug 已存在")
    p = await post_crud.update(db, p, payload)
    await db.commit()
    logger.info("post_updated", post_id=str(p.id))
    return envelope(_to_admin(p).model_dump())


@router.delete("/{post_id}")
async def delete_post(db: DBSession, _: AdminId, post_id: UUID) -> dict:
    """删除文章。"""
    p = await post_crud.get(db, post_id)
    if not p:
        raise NotFoundError("文章不存在")
    await post_crud.remove(db, p)
    await db.commit()
    # 异步清理知识库 chunks（失败不阻塞删除）
    _try_dispatch_ingest_delete(str(post_id))
    logger.info("post_deleted", post_id=str(post_id))
    return envelope({"ok": True})


@router.post("/{post_id}/status")
async def update_status(
    db: DBSession,
    _: AdminId,
    post_id: UUID,
    payload: PostStatusUpdate,
) -> dict:
    """切换状态（发布/草稿/归档）。

    发布时自动填 published_at（仅首次）。
    - draft → published：异步入库
    - published → archived/draft：异步清理 chunks
    """
    p = await post_crud.get_with_channel(db, post_id)
    if not p:
        raise NotFoundError("文章不存在")
    prev_status = p.status
    p = await post_crud.set_status(db, p, payload.status)
    await db.commit()

    # 触发 Celery 入库任务
    if payload.status == "published":
        _try_dispatch_ingest_publish(str(post_id))
    elif prev_status == "published" and payload.status != "published":
        _try_dispatch_ingest_delete(str(post_id))

    logger.info(
        "post_status_changed",
        post_id=str(p.id),
        prev=prev_status,
        status=p.status,
    )
    return envelope(_to_admin(p).model_dump())


def _try_dispatch_ingest_publish(post_id: str) -> None:
    """派发入库任务，失败不阻塞主流程。"""
    try:
        from app.tasks.ingest_tasks import on_post_publish

        on_post_publish.delay(post_id)
    except Exception as e:
        logger.warning("ingest_dispatch_failed", kind="publish", post_id=post_id, error=str(e))


def _try_dispatch_ingest_delete(post_id: str) -> None:
    """派发清理任务，失败不阻塞主流程。"""
    try:
        from app.tasks.ingest_tasks import on_post_delete

        on_post_delete.delay(post_id)
    except Exception as e:
        logger.warning("ingest_dispatch_failed", kind="delete", post_id=post_id, error=str(e))


@router.post("/{post_id}/revalidate")
async def revalidate(_: AdminId, post_id: UUID) -> dict:
    """通知 Next.js 重新生成 SSG。

    P0 简化：直接调用 Next.js on-demand revalidate API。
    """
    # 实际调用放 services/cms.py（P1 实现）；此处占位返回 ok
    logger.info("revalidate_requested", post_id=str(post_id))
    return envelope({"ok": True, "post_id": str(post_id)})
