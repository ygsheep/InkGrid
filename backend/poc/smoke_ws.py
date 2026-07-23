"""WS /ws/chat 端到端验证：创建 session → WS 连接 → 发问 → 收帧。

用法：
    cd backend; $env:PYTHONPATH="."; py -3.14 poc/smoke_ws.py
前提：uvicorn app.main:app 已在 :8000 运行。
"""
import asyncio
import json
import uuid

import httpx
import websockets

API = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/chat"
ANON_ID = str(uuid.uuid4())


async def create_session() -> str:
    """POST /api/chat/sessions 创建会话，返回 session_id。"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{API}/api/chat/sessions",
            json={
                "scope_type": "global",
                "scope_ref": "",
                "title": "smoke ws test",
            },
            headers={"X-Session-Id": ANON_ID},
        )
        r.raise_for_status()
        body = r.json()
        return body["data"]["id"]


async def chat(session_id: str, question: str) -> None:
    """WS 连接 → 发 USER_MESSAGE → 收帧直到 DONE。"""
    url = f"{WS_URL}?session={session_id}&anon_id={ANON_ID}"
    print(f"[ws] connecting {url}")

    async with websockets.connect(url) as ws:
        # 发 USER_MESSAGE 帧
        await ws.send(json.dumps({"type": "user_message", "content": question}))
        print(f"[ws] sent user_message: {question}")

        token_parts: list[str] = []
        citations: list = []
        followups: list = []

        # 收帧循环
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=120.0)
            except asyncio.TimeoutError:
                print("[ws] timeout waiting for frame")
                break

            frame = json.loads(raw)
            ftype = frame.get("type")

            if ftype == "token":
                token_parts.append(frame.get("content", ""))
            elif ftype == "citation":
                citations = frame.get("data", [])
                print(f"[ws] <- citation: {len(citations)} items")
            elif ftype == "followup":
                followups = frame.get("questions", [])
                print(f"[ws] <- followup: {followups}")
            elif ftype == "done":
                print(f"[ws] <- done")
                break
            elif ftype == "error":
                print(f"[ws] <- error: code={frame.get('code')} msg={frame.get('message')}")
                break
            elif ftype == "rate":
                print(f"[ws] <- rate: remaining={frame.get('remaining')}")
            elif ftype == "heartbeat":
                pass  # 心跳忽略
            else:
                print(f"[ws] <- unknown frame: {ftype}")

        answer = "".join(token_parts)
        print(f"\n[ws] answer ({len(answer)} chars):")
        print(answer[:500] if answer else "(empty)")
        if citations:
            print(f"\n[ws] citations ({len(citations)}):")
            for i, c in enumerate(citations):
                print(
                    f"  [{i}] title={c.get('title', '')!r} "
                    f"slug={c.get('article_slug', '')!r}"
                )


async def main():
    print(f"[1] anon_id = {ANON_ID}")

    # 健康检查
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{API}/health")
        print(f"[1] backend health: {r.json()}")

    # 创建 session
    session_id = await create_session()
    print(f"[2] session created: {session_id}")

    # WS 问答
    question = "RAG 有哪些核心组件？分别用什么技术实现？"
    print(f"\n[3] === WS chat ===")
    await chat(session_id, question)

    # 查消息历史
    print(f"\n[4] === message history ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{API}/api/chat/sessions/{session_id}/messages",
            headers={"X-Session-Id": ANON_ID},
        )
        r.raise_for_status()
        msgs = r.json()["data"]["items"]
        for m in msgs:
            print(
                f"  role={m['role']} content_len={len(m['content'])} "
                f"citations={len(m.get('citations') or [])} "
                f"followups={len(m.get('follow_ups') or [])}"
            )
    print("\n[DONE] ws e2e verified")


if __name__ == "__main__":
    asyncio.run(main())
