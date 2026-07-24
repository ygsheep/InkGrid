"""WebSocket 文字流式问答 /ws/chat。

连接参数：
    wss://host/ws/chat?session=<session_id>&anon_id=<anon_id>

帧协议（JSON 文本帧）见 schemas/ws.py 与 plan/后端设计方案.md §5.4。

P1 阶段接入 RAG pipeline（PydanticAI + Milvus + BGE-M3 + reranker）。
"""
import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.logging import get_logger, new_request_id
from app.core.rate_limit import check_chat_anon, check_chat_ip
from app.crud.chat import chat_message, chat_session
from app.db.session import async_session_factory
from app.models.persona import Persona
from app.schemas import ws as ws_constants
from app.services.rag.pipeline import run_rag_pipeline

router = APIRouter()
logger = get_logger("ws.chat")


async def _send_rate(websocket: WebSocket, remaining: int) -> None:
    """发送限流信息帧（前端用于展示剩余次数）。"""
    await websocket.send_json({
        "type": ws_constants.RATE,
        "remaining": remaining,
    })


async def _send_error_and_close(
    websocket: WebSocket, code: str, message: str
) -> None:
    """发送 error 帧并关闭连接。"""
    await websocket.send_json({
        "type": ws_constants.ERROR,
        "code": code,
        "message": message,
    })
    await websocket.close(code=1008)


# ===== 路由 =====


@router.websocket("/ws/chat")
async def chat_endpoint(
    websocket: WebSocket,
    session: str,
    anon_id: str | None = None,
) -> None:
    """WS 文字问答端点。

    query 参数：
        session: 会话 ID（必需，由 POST /api/chat/sessions 创建）
        anon_id: 匿名访客 ID（用于限流，可选）
    """
    await websocket.accept()
    new_request_id()  # 注入 request_id 到上下文

    # 校验 session
    try:
        session_id = UUID(str(session))
    except ValueError:
        await _send_error_and_close(
            websocket, ws_constants.ERR_INVALID, "session 参数非法"
        )
        return

    # 加载会话 + persona
    async with async_session_factory() as db:
        sess = await chat_session.get(db, session_id)
        if not sess:
            await _send_error_and_close(
                websocket, ws_constants.ERR_INVALID, "会话不存在"
            )
            return
        if anon_id and sess.anon_id and sess.anon_id != anon_id:
            await _send_error_and_close(
                websocket, ws_constants.ERR_INVALID, "会话归属不匹配"
            )
            return
        if not anon_id:
            anon_id = sess.anon_id

        # 加载 persona（如果有）
        persona_name = ""
        persona_prompt = ""
        if sess.persona_id:
            persona = await db.get(Persona, sess.persona_id)
            if persona:
                persona_name = persona.name or ""
                persona_prompt = persona.system_prompt or ""

        scope_type = sess.scope_type or "global"
        scope_ref = sess.scope_ref or ""

    # 提取 IP
    client_ip = (
        websocket.client.host if websocket.client else "0.0.0.0"
    )

    logger.info(
        "ws_connected",
        session_id=str(session_id),
        anon_id=anon_id,
        ip=client_ip,
        scope=f"{scope_type}:{scope_ref}",
    )

    # 生成取消事件（用于 stop 帧中断流式输出）
    cancel_event = asyncio.Event()

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("ws_disconnected", session_id=str(session_id))
                break

            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": ws_constants.ERROR,
                    "code": ws_constants.ERR_INVALID,
                    "message": "帧不是合法 JSON",
                })
                continue

            ftype = frame.get("type")

            if ftype == ws_constants.HEARTBEAT:
                await websocket.send_json({"type": ws_constants.HEARTBEAT})
                continue

            if ftype == ws_constants.STOP:
                cancel_event.set()
                continue

            if ftype != ws_constants.USER_MESSAGE:
                await websocket.send_json({
                    "type": ws_constants.ERROR,
                    "code": ws_constants.ERR_INVALID,
                    "message": f"未知帧类型：{ftype}",
                })
                continue

            content = (frame.get("content") or "").strip()
            if not content:
                await websocket.send_json({
                    "type": ws_constants.ERROR,
                    "code": ws_constants.ERR_INVALID,
                    "message": "消息内容不能为空",
                })
                continue

            # 限流：IP 20/min + anon_id 50/day
            try:
                await check_chat_ip(client_ip)
                if anon_id:
                    await check_chat_anon(anon_id)
            except Exception as e:
                from app.core.errors import RateLimitError

                if isinstance(e, RateLimitError):
                    await websocket.send_json({
                        "type": ws_constants.ERROR,
                        "code": ws_constants.ERR_RATE_LIMITED,
                        "message": e.message,
                        "data": e.data,
                    })
                else:
                    logger.exception("rate_check_error", error=str(e))
                    await websocket.send_json({
                        "type": ws_constants.ERROR,
                        "code": ws_constants.ERR_INTERNAL,
                        "message": "限流检查异常",
                    })
                continue

            # 重置取消事件
            cancel_event.clear()

            # 持久化 user 消息
            async with async_session_factory() as db:
                await chat_message.add(
                    db,
                    session_id=session_id,
                    role="user",
                    content=content,
                )
                await db.commit()

            # 流式输出 RAG 回复
            answer, citations, followups = await _stream_rag_reply(
                websocket,
                content,
                scope_type,
                scope_ref,
                persona_name,
                persona_prompt,
                cancel_event,
            )

            # 持久化 assistant 消息（含 citations/followups）
            # answer 为空说明 pipeline 异常或 LLM 未返回内容，
            # error 帧已通过 websocket 发给前端，这里不存空消息避免污染历史
            if answer:
                async with async_session_factory() as db:
                    await chat_message.add(
                        db,
                        session_id=session_id,
                        role="assistant",
                        content=answer,
                        citations=citations or None,
                        follow_ups=followups or None,
                    )
                    await db.commit()
            else:
                logger.warning(
                    "empty_answer_skipped",
                    session_id=str(session_id),
                    query=content[:50],
                )

    except WebSocketDisconnect:
        logger.info("ws_disconnected", session_id=str(session_id))
    except Exception as e:
        logger.exception("ws_error", session_id=str(session_id), error=str(e))
        try:
            await _send_error_and_close(
                websocket, ws_constants.ERR_INTERNAL, "服务器内部错误"
            )
        except Exception:
            pass


async def _stream_rag_reply(
    websocket: WebSocket,
    question: str,
    scope_type: str,
    scope_ref: str,
    persona_name: str,
    persona_prompt: str,
    cancel_event: asyncio.Event,
) -> tuple[str, list[dict], list[str]]:
    """带取消支持的 RAG 流式输出。

    遍历 run_rag_pipeline generator，发送帧，收集 answer/citations/followups。
    cancel_event 被 set 时中断（用户 stop 帧）。

    Returns:
        (answer, citations, followups)
    """
    answer_parts: list[str] = []
    citations: list[dict] = []
    followups: list[str] = []

    try:
        async for frame in run_rag_pipeline(
            query=question,
            scope_type=scope_type,
            scope_ref=scope_ref,
            persona_name=persona_name,
            persona_system_prompt=persona_prompt,
        ):
            # 检查取消
            if cancel_event.is_set():
                logger.info("stream_cancelled", query=question[:50])
                break

            await websocket.send_json(frame)

            # 收集结果用于持久化
            ftype = frame.get("type")
            if ftype == ws_constants.TOKEN:
                answer_parts.append(frame.get("content", ""))
            elif ftype == ws_constants.CITATION:
                citations = frame.get("data", [])
            elif ftype == ws_constants.FOLLOWUP:
                followups = frame.get("questions", [])

    except asyncio.CancelledError:
        logger.info("stream_task_cancelled", query=question[:50])
    except Exception as e:
        logger.exception("stream_error", query=question[:50], error=str(e))
        # 降级：发送错误提示
        await websocket.send_json({
            "type": ws_constants.ERROR,
            "code": ws_constants.ERR_INTERNAL,
            "message": "回答生成失败",
        })

    return "".join(answer_parts), citations, followups
