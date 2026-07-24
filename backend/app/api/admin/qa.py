"""后台 Q&A 审核路由：GET/PATCH /admin/qa[/:id]。

- GET /admin/qa?status=pending — 列出 Q&A（可按状态过滤）
- GET /admin/qa/{id} — Q&A 详情
- PATCH /admin/qa/{id} — 审核（approve/reject/编辑内容）
- POST /admin/qa/{id}/reindex — 审核通过后写入 Milvus
"""
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.crud import qa as qa_crud
from app.deps import AdminId, DBSession
from app.schemas.common import envelope
from app.schemas.qa import QaPairOut, QaReviewIn

router = APIRouter(prefix="/qa")
logger = get_logger("admin.qa")


def _to_out(qa) -> dict:
    """ORM QaPair → 输出 dict。"""
    article_title = ""
    if hasattr(qa, "article") and qa.article:
        article_title = qa.article.title or ""
    return QaPairOut(
        id=str(qa.id),
        article_id=str(qa.article_id),
        question=qa.question,
        answer=qa.answer,
        status=qa.status,
        milvus_chunk_id=qa.milvus_chunk_id,
        created_at=qa.created_at,
        updated_at=qa.updated_at,
        article_title=article_title,
    ).model_dump()


@router.get("")
async def list_qa(
    db: DBSession,
    _: AdminId,
    status: str | None = Query(None, description="pending | approved | rejected"),
    article_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> dict:
    """Q&A 列表（可按状态/文章过滤）。"""
    offset = (page - 1) * size

    if status == "pending":
        items = await qa_crud.list_pending(db, offset=offset, limit=size)
        total = len(items)  # 简化：pending 列表不分页
    elif article_id:
        items = await qa_crud.list_by_article(db, article_id, status=status)
        total = len(items)
    else:
        # 默认列出全部（简化实现）
        items = await qa_crud.list_pending(db, offset=offset, limit=size)
        total = len(items)

    return envelope({
        "items": [_to_out(qa) for qa in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.get("/{qa_id}")
async def get_qa(db: DBSession, _: AdminId, qa_id: UUID) -> dict:
    """Q&A 详情。"""
    qa = await qa_crud.get(db, qa_id)
    if not qa:
        raise NotFoundError("Q&A 不存在")
    return envelope(_to_out(qa))


@router.patch("/{qa_id}")
async def review_qa(
    db: DBSession,
    _: AdminId,
    qa_id: UUID,
    payload: QaReviewIn,
) -> dict:
    """审核 Q&A：修改内容 + 设置状态。

    - approved → 更新 PG 状态，但不自动写 Milvus（需调用 reindex）
    - rejected → 更新 PG 状态
    - 可同时修改 question / answer 内容
    """
    qa = await qa_crud.get(db, qa_id)
    if not qa:
        raise NotFoundError("Q&A 不存在")

    if payload.status not in ("approved", "rejected"):
        raise ValidationError("status 只能是 approved 或 rejected")

    # 修改内容
    if payload.question is not None:
        qa.question = payload.question
    if payload.answer is not None:
        qa.answer = payload.answer

    # 更新状态
    await qa_crud.update_status(db, qa, payload.status)
    await db.commit()

    logger.info(
        "qa_reviewed",
        qa_id=str(qa_id),
        status=payload.status,
    )
    return envelope(_to_out(qa))


@router.post("/{qa_id}/reindex")
async def reindex_qa(db: DBSession, _: AdminId, qa_id: UUID) -> dict:
    """审核通过后写入 Milvus（或更新已存在的向量）。

    流程：
    1. 校验 Q&A 存在且 status=approved
    2. 如果已有 milvus_chunk_id → 先删旧向量
    3. 写入新向量
    4. 回填 milvus_chunk_id
    """
    from app.services.qa.milvus_writer import (
        delete_qa_from_milvus,
        write_qa_to_milvus,
    )

    qa = await qa_crud.get(db, qa_id)
    if not qa:
        raise NotFoundError("Q&A 不存在")

    if qa.status != "approved":
        raise ValidationError("只能对 approved 状态的 Q&A 执行 reindex")

    # 删旧向量
    if qa.milvus_chunk_id:
        await delete_qa_from_milvus(qa)

    # 写入新向量
    chunk_id = await write_qa_to_milvus(db, qa)

    # 回填
    await qa_crud.update_status(
        db, qa, "approved", milvus_chunk_id=chunk_id,
    )
    await db.commit()

    logger.info("qa_reindexed", qa_id=str(qa_id), chunk_id=chunk_id)
    return envelope({"qa_id": str(qa_id), "milvus_chunk_id": chunk_id})
