"""PydanticAI Agent 封装：带 system prompt + context 的 LLM 流式生成。

设计参考：plan/后端设计方案.md §6.7
- 单 Agent + 线性管道：retrieve/rerank 在 agent 之前执行（管道节点）
- agent 只负责接收 context + query，流式生成带 [n] 引用标注的回答
- system_prompt 通过 run_stream(instructions=...) 动态注入（人设/范围每次不同）
"""
from collections.abc import AsyncIterator

from pydantic_ai import Agent

from app.core.logging import get_logger
from app.services.llm.base import build_llm_model
from app.services.llm.prompt import build_system_prompt

logger = get_logger("rag.agent")


class RAGAgent:
    """PydanticAI Agent 封装。

    Agent 实例在首次调用时创建（model 固定），system_prompt 每次 run_stream
    通过 instructions 参数动态注入。
    """

    def __init__(self) -> None:
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        """懒加载 Agent 单例。"""
        if self._agent is None:
            model = build_llm_model()
            self._agent = Agent(model=model)
            logger.info("rag_agent_created")
        return self._agent

    async def stream_answer(
        self,
        query: str,
        context: str,
        persona_name: str = "",
        persona_system_prompt: str = "",
        scope_type: str = "global",
        scope_ref: str = "",
    ) -> AsyncIterator[str]:
        """流式生成回答。

        Args:
            query: 用户问题
            context: 检索到的上下文（已由 context_builder 组装）
            persona_name: 人设名称
            persona_system_prompt: 人设系统提示词
            scope_type: global | channel | article
            scope_ref: channel slug 或 article slug

        Yields:
            增量 token 字符串
        """
        from datetime import date

        agent = self._get_agent()
        system_prompt = build_system_prompt(
            persona_name=persona_name,
            persona_system_prompt=persona_system_prompt,
            scope_type=scope_type,
            scope_ref=scope_ref,
            current_date=str(date.today()),
        )

        # 组装 user prompt：上下文 + 问题
        user_prompt = f"参考以下资料回答问题，引用处标注 [n]：\n\n{context}\n\n问题：{query}"

        logger.info(
            "agent_stream_start",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            persona=persona_name or "default",
        )

        async with agent.run_stream(user_prompt, instructions=system_prompt) as result:
            async for token in result.stream_text(delta=True):
                yield token


# 单例
rag_agent = RAGAgent()
