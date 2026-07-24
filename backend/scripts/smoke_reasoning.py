"""验证 RAGAgent.stream_answer 的 reasoning + content 流式输出。

绕过检索管道，直接用空 context 调用 LLM，确认：
1. reasoning 模型先输出 reasoning 帧（思考过程）
2. 然后输出 content 帧（正式回答）
3. 非 reasoning 模型只输出 content 帧

用法：
    cd backend
    conda run -n backend --no-capture-output python scripts/smoke_reasoning.py
"""
import asyncio
import sys
import time

sys.path.insert(0, ".")


async def main() -> None:
    from app.core.logging import configure_logging, get_logger
    from app.services.rag.agent import rag_agent

    configure_logging(debug=False)
    logger = get_logger("smoke.reasoning")

    print("=" * 60)
    print("Reasoning 流式输出验证")
    print("=" * 60)

    question = "你好，请用一句话介绍你自己。"
    # 空 context，让 LLM 直接回答（不依赖知识库）
    context = "（无参考资料）"

    print(f"\nQ: {question}")
    print(f"Context: {context}")
    print("\n流式输出：")
    print("-" * 60)

    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    t0 = time.time()
    first_reasoning_time: float | None = None
    first_content_time: float | None = None

    try:
        async for kind, delta in rag_agent.stream_answer(
            query=question,
            context=context,
            persona_name="",
            persona_system_prompt="",
            scope_type="global",
            scope_ref="",
        ):
            if kind == "reasoning":
                if first_reasoning_time is None:
                    first_reasoning_time = time.time() - t0
                    print(f"\n[reasoning 开始 @ {first_reasoning_time:.1f}s]")
                reasoning_parts.append(delta)
                print(delta, end="", flush=True)
            elif kind == "content":
                if first_content_time is None:
                    first_content_time = time.time() - t0
                    print(f"\n\n[content 开始 @ {first_content_time:.1f}s]")
                content_parts.append(delta)
                print(delta, end="", flush=True)
    except Exception as e:
        print(f"\n\n✗ 失败: {type(e).__name__}: {e}")
        logger.exception("smoke_reasoning_failed", error=str(e))
        sys.exit(1)

    elapsed = time.time() - t0
    reasoning_text = "".join(reasoning_parts)
    content_text = "".join(content_parts)

    print(f"\n\n{'-' * 60}")
    print(f"总耗时:        {elapsed:.1f}s")
    print(f"首 reasoning:  {first_reasoning_time:.1f}s" if first_reasoning_time else "首 reasoning:  无")
    print(f"首 content:    {first_content_time:.1f}s" if first_content_time else "首 content:    无")
    print(f"reasoning 长度: {len(reasoning_text)} 字符")
    print(f"content 长度:   {len(content_text)} 字符")

    print(f"\n{'=' * 60}")
    if reasoning_text and content_text:
        print("✓ reasoning 模型验证通过：思考过程 + 正式回答都正常输出")
    elif content_text and not reasoning_text:
        print("✓ 非 reasoning 模型：只有 content 输出（正常）")
    elif reasoning_text and not content_text:
        print("✗ 只有 reasoning 没有 content（max_tokens 不够？）")
        sys.exit(1)
    else:
        print("✗ reasoning 和 content 都为空")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
