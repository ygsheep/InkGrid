"""WebSocket 文字流式问答 /ws/chat。

连接参数：
    wss://host/ws/chat?session=<session_id>&anon_id=<anon_id>

帧协议（JSON 文本帧）见 schemas/ws.py 与 plan/后端设计方案.md §5.4。

P0 阶段使用 mock LLM：固定回复 + 模拟 token 流。
真实 RAG/LLM 接入在 P1+。
"""
import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger, new_request_id
from app.core.rate_limit import check_chat_anon, check_chat_ip
from app.crud.chat import chat_message, chat_session
from app.db.session import async_session_factory
from app.schemas import ws as ws_constants

router = APIRouter()
logger = get_logger("ws.chat")


# ===== Mock LLM =====

_MOCK_REPLY_TEMPLATE = (
    "（这是 P0 阶段的 mock 回答）\n\n"
    "你问的是：「{question}」\n\n"
    "当前后端尚未接入 RAG 与 LLM，待 P1 阶段接入后会基于文章知识库作答。"
)
_MOCK_FOLLOWUPS = ["什么是 InkGrid？", "文章如何发布？", "频道和人设的区别？"]


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

    # 加载会话
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

    # 提取 IP（WS 用 client.host）
    client_ip = (
        websocket.client.host if websocket.client else "0.0.0.0"
    )

    logger.info(
        "ws_connected",
        session_id=str(session_id),
        anon_id=anon_id,
        ip=client_ip,
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
                # RateLimitError 或其他
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

            # 流式输出 mock 回复
            try:
                reply = await _stream_mock_reply_with_cancel(
                    websocket, content, cancel_event
                )
            except asyncio.CancelledError:
                reply = "（已中断）"

            # 发送推荐追问
            await websocket.send_json({
                "type": ws_constants.FOLLOWUP,
                "questions": _MOCK_FOLLOWUPS,
            })

            # 持久化 assistant 消息
            async with async_session_factory() as db:
                await chat_message.add(
                    db,
                    session_id=session_id,
                    role="assistant",
                    content=reply,
                    follow_ups=_MOCK_FOLLOWUPS,
                )
                await db.commit()

            # 发送 done
            await websocket.send_json({"type": ws_constants.DONE})

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


async def _stream_mock_reply_with_cancel(
    websocket: WebSocket, question: str, cancel_event: asyncio.Event
) -> str:
    """带取消支持的 mock 流式输出。"""
    reply = _MOCK_REPLY_TEMPLATE.format(question=question)
    chunks = [reply[i : i + 2] for i in range(0, len(reply), 2)]
    sent = []
    for chunk in chunks:
        if cancel_event.is_set():
            break
        await websocket.send_json({"type": ws_constants.TOKEN, "content": chunk})
        sent.append(chunk)
        await asyncio.sleep(0.05)
    return "".join(sent) if sent else reply
