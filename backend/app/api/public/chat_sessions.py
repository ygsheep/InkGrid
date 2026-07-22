"""公开会话 REST：POST /api/chat/sessions, GET /api/chat/sessions, GET /api/chat/sessions/:id/messages。

公开接口：靠 X-Session-Id 区分匿名访客。
"""
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.errors import NotFoundError, ValidationError
from app.crud.chat import chat_message, chat_session
from app.deps import AnonId, ClientIP, DBSession
from app.schemas.chat import ChatMessageOut, ChatSessionCreate, ChatSessionOut
from app.schemas.common import Page, envelope

router = APIRouter(prefix="/chat")


@router.post("/sessions")
async def create_session(
    payload: ChatSessionCreate,
    db: DBSession,
    anon_id: AnonId,
    ip: ClientIP,
) -> dict:
    """创建会话。

    前端必须传 X-Session-Id 头，作为 anon_id。
    入参可指定 persona_id / scope_type / scope_ref / title。
    """
    if not anon_id:
        raise ValidationError("缺少 X-Session-Id 头")
    # 限流：anon_id 每日 50 问（这里只做创建计数，实际问答在 WS 里）
    # 创建会话不消耗问答配额，只做 IP 限流（已在中间件层）
    payload.anon_id = anon_id
    s = await chat_session.create(db, payload)
    await db.commit()
    return envelope(ChatSessionOut(
        id=str(s.id),
        anon_id=s.anon_id,
        persona_id=str(s.persona_id) if s.persona_id else None,
        scope_type=s.scope_type,
        scope_ref=s.scope_ref,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
    ).model_dump())


@router.get("/sessions")
async def list_sessions(
    db: DBSession,
    anon_id: AnonId,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """当前 anon_id 的会话列表。"""
    if not anon_id:
        return envelope({"items": [], "total": 0, "page": page, "size": size})
    offset = (page - 1) * size
    items, total = await chat_session.list_by_anon(db, anon_id, offset=offset, limit=size)
    page_obj = Page[ChatSessionOut](
        items=[
            ChatSessionOut(
                id=str(s.id),
                anon_id=s.anon_id,
                persona_id=str(s.persona_id) if s.persona_id else None,
                scope_type=s.scope_type,
                scope_ref=s.scope_ref,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in items
        ],
        total=total,
        page=page,
        size=size,
    )
    return envelope(page_obj.model_dump())


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    db: DBSession,
    anon_id: AnonId,
    session_id: UUID,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """会话消息历史。"""
    s = await chat_session.get(db, session_id)
    if not s:
        raise NotFoundError("会话不存在")
    # 校验 anon_id 归属
    if anon_id and s.anon_id and s.anon_id != anon_id:
        raise NotFoundError("会话不存在")
    msgs = await chat_message.list_by_session(db, session_id, limit=limit)
    page_obj = Page[ChatMessageOut](
        items=[
            ChatMessageOut(
                id=str(m.id),
                session_id=str(m.session_id),
                role=m.role,
                content=m.content,
                citations=m.citations,
                follow_ups=m.follow_ups,
                created_at=m.created_at,
            )
            for m in msgs
        ],
        total=len(msgs),
        page=1,
        size=limit,
    )
    return envelope(page_obj.model_dump())
