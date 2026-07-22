"""会话与消息 CRUD。

P0 阶段仅实现会话创建、按 anon_id 列表、消息追加与历史。
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import ChatSessionCreate


class CRUDChatSession:
    """会话数据访问层。"""

    model = ChatSession

    async def create(self, db: AsyncSession, obj_in: ChatSessionCreate) -> ChatSession:
        """新建会话。"""
        data = obj_in.model_dump(exclude_unset=True)
        db_obj = ChatSession(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, session_id: UUID) -> ChatSession | None:
        """按 id 取会话。"""
        return await db.get(ChatSession, session_id)

    async def list_by_anon(
        self,
        db: AsyncSession,
        anon_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ChatSession], int]:
        """按 anon_id 列出会话。"""
        stmt = (
            select(ChatSession)
            .where(ChatSession.anon_id == anon_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())
        total = (
            await db.execute(
                select(func.count())
                .select_from(ChatSession)
                .where(ChatSession.anon_id == anon_id)
            )
        ).scalar_one()
        return items, total


class CRUDChatMessage:
    """消息数据访问层。"""

    model = ChatMessage

    async def add(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        role: str,
        content: str,
        citations: list | None = None,
        follow_ups: list[str] | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
    ) -> ChatMessage:
        """追加一条消息。"""
        db_obj = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
            follow_ups=follow_ups,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def list_by_session(
        self,
        db: AsyncSession,
        session_id: UUID,
        *,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """按 session 列出消息（按 created_at asc）。"""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())


chat_session = CRUDChatSession()
chat_message = CRUDChatMessage()
