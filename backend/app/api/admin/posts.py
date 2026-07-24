"""后台文章路由：GET/POST/PATCH/DELETE /admin/posts[/:id]、状态切换、revalidate。

发布（status=published）触发入库任务（P0-9 接入）。
"""
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.crud.post import post as post_crud
from app.deps import AdminId, DBSession
from app.ingest.parser import parse_markdown
from app.ingest.toc import headings_to_toc
from app.schemas.common import Page, envelope
from app.schemas.post import (
    ArticleAdmin,
    PostCreate,
    PostStatusUpdate,
    PostUpdate,
)
from app.services.cms import (
    _paths_for_post,
    _tags_for_post,
    notify_revalidate,
)
from app.services.post_derive import (
    calculate_reading_time,
    derive_slug,
    generate_excerpt,
    generate_toc,
)
from app.services.upload_security import (
    UploadSecurityError,
    validate_markdown_file,
)
from app.utils.slug import slugify

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
        channel_id=str(p.channel_id) if p.channel_id else None,
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


def _apply_derived_fields(
    payload: PostCreate | PostUpdate,
) -> None:
    """对未显式提供的派生字段做自动填充。

    - slug 为空 → 从 title 生成
    - excerpt 未提供 → 从 content_md 首段提取
    - reading_time 未提供 → 按字数估算
    - toc 未提供 → 从 content_md 标题生成

    设置属性后同步注册到 __pydantic_fields_set__,确保 model_dump(exclude_unset=True)
    能包含这些字段(CRUDBase 依赖 exclude_unset 决定写入哪些列)。
    """
    content_md = getattr(payload, "content_md", None)
    title = getattr(payload, "title", None)

    def _set(field: str, value: object) -> None:
        """设置属性并注册到 fields_set。"""
        setattr(payload, field, value)
        # Pydantic v2: model_dump(exclude_unset=True) 基于 __pydantic_fields_set__
        payload.__pydantic_fields_set__.add(field)  # type: ignore[attr-defined]

    # slug:空值时从 title 生成
    if title and not getattr(payload, "slug", None):
        _set("slug", derive_slug(title))

    if content_md:
        # excerpt:None 时自动生成
        if getattr(payload, "excerpt", None) is None:
            _set("excerpt", generate_excerpt(content_md))
        # reading_time:None 时自动计算
        if getattr(payload, "reading_time", None) is None:
            _set("reading_time", calculate_reading_time(content_md))
        # toc:None 时自动生成
        if getattr(payload, "toc", None) is None:
            _set("toc", generate_toc(content_md))


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
    # 自动填充未提供的派生字段(slug/excerpt/reading_time/toc)
    _apply_derived_fields(payload)
    # slug 唯一性预检
    existing = await post_crud.get_by_slug(db, payload.slug)
    if existing:
        raise ConflictError("slug 已存在")
    p = await post_crud.create(db, payload)
    await db.commit()
    # 重新加载 channel 关系（async session 不支持懒加载）
    p = await post_crud.get_with_channel(db, p.id)
    logger.info("post_created", post_id=str(p.id), slug=p.slug)
    # 发布状态的文章立即通知前端 revalidate + 触发 RAG 入库
    if p.status == "published":
        await notify_revalidate(
            paths=_paths_for_post(p.slug),
            tags=_tags_for_post(p.slug),
        )
        _try_dispatch_ingest_publish(str(p.id))
        await _try_sync_meili_upsert(p)
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
    """更新文章。

    内容变更（content_md/title/tags）且文章为 published 时触发重新入库；
    状态从 published 切出时清理 chunks。
    """
    p = await post_crud.get_with_channel(db, post_id)
    if not p:
        raise NotFoundError("文章不存在")
    prev_status = p.status
    # 自动填充未提供的派生字段(content_md 变更时重新生成 toc/reading_time 等)
    _apply_derived_fields(payload)
    # slug 变更时预检
    if payload.slug and payload.slug != p.slug:
        existing = await post_crud.get_by_slug(db, payload.slug)
        if existing and existing.id != p.id:
            raise ConflictError("slug 已存在")
    p = await post_crud.update(db, p, payload)
    await db.commit()
    logger.info("post_updated", post_id=str(p.id))

    # RAG 入库触发：
    # - 仍是 published 且内容字段被修改 → 重新入库（删旧建新，幂等）
    # - 从 published 切到非 published → 清理 chunks
    content_changed = any(
        f in payload.__pydantic_fields_set__
        for f in ("content_md", "title", "tags")
    )
    if p.status == "published" and content_changed:
        _try_dispatch_ingest_publish(str(p.id))
        await _try_sync_meili_upsert(p)
    elif prev_status == "published" and p.status != "published":
        _try_dispatch_ingest_delete(str(p.id))
        await _try_sync_meili_delete(str(p.id))

    await notify_revalidate(
        paths=_paths_for_post(p.slug),
        tags=_tags_for_post(p.slug),
    )
    return envelope(_to_admin(p).model_dump())


@router.delete("/{post_id}")
async def delete_post(db: DBSession, _: AdminId, post_id: UUID) -> dict:
    """删除文章。"""
    p = await post_crud.get(db, post_id)
    if not p:
        raise NotFoundError("文章不存在")
    slug = p.slug
    await post_crud.remove(db, p)
    await db.commit()
    # 异步清理知识库 chunks（失败不阻塞删除）
    _try_dispatch_ingest_delete(str(post_id))
    await _try_sync_meili_delete(str(post_id))
    logger.info("post_deleted", post_id=str(post_id))
    await notify_revalidate(
        paths=_paths_for_post(slug),
        tags=_tags_for_post(slug),
    )
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
        await _try_sync_meili_upsert(p)
    elif prev_status == "published" and payload.status != "published":
        _try_dispatch_ingest_delete(str(post_id))
        await _try_sync_meili_delete(str(post_id))

    logger.info(
        "post_status_changed",
        post_id=str(p.id),
        prev=prev_status,
        status=p.status,
    )
    # 状态变更影响公开列表可见性，统一失效文章相关缓存
    await notify_revalidate(
        paths=_paths_for_post(p.slug),
        tags=_tags_for_post(p.slug),
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


async def _try_sync_meili_upsert(p) -> None:
    """同步文章到 Meilisearch，失败不阻断主流程。"""
    try:
        from app.services.search import upsert_post_orm

        ch_slug = p.channel.slug if p.channel else ""
        ch_name = p.channel.name if p.channel else ""
        await upsert_post_orm(p, ch_slug, ch_name)
    except Exception as e:
        logger.warning("meili_sync_failed", kind="upsert", post_id=str(p.id), error=str(e))


async def _try_sync_meili_delete(post_id: str) -> None:
    """从 Meilisearch 删除文章，失败不阻断主流程。"""
    try:
        from app.services.search import delete_post

        await delete_post(post_id)
    except Exception as e:
        logger.warning("meili_sync_failed", kind="delete", post_id=post_id, error=str(e))


@router.post("/{post_id}/revalidate")
async def revalidate(db: DBSession, _: AdminId, post_id: UUID) -> dict:
    """手动触发指定文章的 Next.js revalidate。

    通常 CRUD 后会自动调用，此端点用于排错或手动重试。
    """
    p = await post_crud.get(db, post_id)
    slug = p.slug if p else None
    logger.info("revalidate_requested", post_id=str(post_id), slug=slug)
    await notify_revalidate(
        paths=_paths_for_post(slug),
        tags=_tags_for_post(slug),
    )
    return envelope({"ok": True, "post_id": str(post_id), "slug": slug})


def _extract_title_and_slug(content_md: str, filename: str) -> tuple[str, str]:
    """从 Markdown 内容提取标题与 slug。

    - title:首个 # 一级标题;无则用文件名(去 .md)
    - slug:title 经 slugify 生成
    """
    import re

    # 找首个一级标题
    for line in content_md.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            title = m.group(1).strip()
            return title, slugify(title)

    # 兜底:文件名去 .md
    base = filename
    if base.lower().endswith(".md"):
        base = base[:-3]
    title = base.strip() or "untitled"
    return title, slugify(title) or "untitled"


async def _ensure_unique_slug(db: AsyncSession, base_slug: str) -> str:
    """slug 冲突时自动加 -2/-3 后缀直到唯一。"""
    candidate = base_slug
    suffix = 2
    while await post_crud.get_by_slug(db, candidate):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate


@router.post("/upload")
async def upload_post_md(
    db: DBSession,
    _: AdminId,
    files: list[UploadFile] = File(..., description="多文件(.md/.markdown)"),
    channel_id: UUID = Form(..., description="归属频道 ID"),
) -> dict:
    """批量上传 Markdown 文件 → 解析 → 创建草稿 → 返回 {created, failed}。

    流程（逐文件）:
    1. 安全验证(扩展名/MIME/大小/NUL/UTF-8)
    2. 提取 title 与 slug(首 # 标题优先,文件名兜底)
    3. slug 冲突时自动加 -2/-3 后缀
    4. 解析 headings 生成 toc
    5. 创建 status=draft 文章(不触发 RAG 入库)

    多文件时逐文件处理，单个文件失败（校验/解析）不阻断其他文件，
    失败项进 failed 列表（含 filename + reason），成功项进 created 列表。

    RAG 入库在文章发布时由 update_status 触发,本接口不调用。
    """
    if not files:
        raise AppError("未提供文件", status_code=400, code=4000)

    # 循环内只收集 post_id，commit 后统一 get_with_channel 预加载关系再序列化
    # （异步 session 不支持 lazy load，_to_admin 访问 p.channel 会抛 MissingGreenlet）
    created_ids: list[UUID] = []
    failed: list[dict] = []

    for file in files:
        filename = file.filename or "untitled.md"

        # 1. 安全验证
        try:
            content_md = validate_markdown_file(file)
        except UploadSecurityError as e:
            failed.append({"filename": filename, "reason": str(e)})
            continue

        # 2. 提取 title 与 slug
        try:
            title, base_slug = _extract_title_and_slug(content_md, filename)
            # 3. slug 唯一化
            slug = await _ensure_unique_slug(db, base_slug)
            # 4. 生成 toc
            parsed = parse_markdown(title=title, content_md=content_md, slug=slug)
            toc = headings_to_toc(parsed.headings)

            # 5. 创建草稿
            payload = PostCreate(
                slug=slug,
                title=title,
                content_md=content_md,
                channel_id=channel_id,
                status="draft",
                toc=toc,
            )
            # 自动填充 excerpt / reading_time(toc 已显式提供,不会覆盖)
            _apply_derived_fields(payload)
            p = await post_crud.create(db, payload)
            created_ids.append(p.id)
        except Exception as e:
            logger.warning(
                "post_upload_failed", filename=filename, error=str(e)
            )
            failed.append({"filename": filename, "reason": f"解析/创建失败: {e}"})
            continue

    # 统一提交：所有成功的草稿一并持久化
    await db.commit()

    # commit 后统一重新加载（含 channel 关系）用于响应
    reloaded: list[dict] = []
    for post_id in created_ids:
        p = await post_crud.get_with_channel(db, post_id)
        if p:
            reloaded.append(_to_admin(p).model_dump())
        else:
            logger.warning("post_missing_after_commit", post_id=str(post_id))
            reloaded.append({"id": str(post_id), "status": "missing"})

    logger.info(
        "posts_batch_uploaded",
        channel_id=str(channel_id),
        created=len(reloaded),
        failed=len(failed),
    )
    return envelope({"created": reloaded, "failed": failed})
