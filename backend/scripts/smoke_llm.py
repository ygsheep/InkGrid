"""最小 LLM 冒烟脚本：验证 PydanticAI + LM Studio 流式输出。

不走 RAG 管道，只验证：
1. build_llm_model() 能构造 OpenAIChatModel
2. Agent.run_stream() 能收到流式 token
3. reasoning 模型的 content 字段被正确读取（reasoning_content 不干扰）

用法：
    cd backend
    conda activate backend
    set PYTHONPATH=.
    python scripts/smoke_llm.py
"""
import asyncio
import sys
import time

sys.path.insert(0, ".")


async def main() -> None:
    from pydantic_ai import Agent

    from app.config import get_settings
    from app.core.logging import configure_logging, get_logger
    from app.services.llm.base import build_llm_model

    configure_logging(debug=False)
    logger = get_logger("smoke.llm")
    settings = get_settings()

    print("=" * 60)
    print("LLM 冒烟测试")
    print(f"  Provider:  {settings.llm_provider}")
    print(f"  Base URL:  {settings.llm_base_url}")
    print(f"  Model:     {settings.llm_model}")
    print(f"  MaxTokens: {settings.llm_max_tokens}")
    print(f"  Timeout:   {settings.llm_request_timeout}s")
    print("=" * 60)

    # 1. 构造 model
    print("\n[1/3] 构造 PydanticAI Model...")
    model = build_llm_model()
    agent = Agent(model=model)
    print("  ✓ Agent 创建成功")

    # 2. 流式生成
    print("\n[2/3] 流式生成中...")
    question = "你好，请用一句话介绍你自己。"
    system_prompt = "你是一个简洁的 AI 助手，用中文回答。"

    print(f"  Q: {question}")
    print(f"  System: {system_prompt}")
    print(f"  A: ", end="", flush=True)

    tokens: list[str] = []
    t0 = time.time()
    first_token_time: float | None = None

    try:
        async with agent.run_stream(question, instructions=system_prompt) as result:
            async for token in result.stream_text(delta=True):
                if first_token_time is None:
                    first_token_time = time.time() - t0
                tokens.append(token)
                print(token, end="", flush=True)

    except Exception as e:
        print(f"\n\n✗ 失败: {type(e).__name__}: {e}")
        logger.exception("smoke_llm_failed", error=str(e))
        sys.exit(1)

    elapsed = time.time() - t0
    answer = "".join(tokens)

    print(f"\n")
    print(f"  首 token 延迟: {first_token_time:.1f}s" if first_token_time else "  首 token: 未收到")
    print(f"  总耗时:        {elapsed:.1f}s")
    print(f"  Token 数:      {len(tokens)}")
    print(f"  回答长度:      {len(answer)} 字符")

    # 3. 判定
    print("\n[3/3] 判定...")
    if not answer.strip():
        print("✗ 回答为空 — PydanticAI 未收到 content（可能 reasoning 模型的 content 被跳过）")
        sys.exit(1)

    print("✓ 回答非空，LLM 流式输出正常")
    print("\n" + "=" * 60)
    print("✓ LLM 冒烟测试通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
