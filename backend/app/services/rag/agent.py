"""RAGAgent：带 system prompt + context 的 LLM 流式生成。

设计参考：plan/后端设计方案.md §6.7
- 单 Agent + 线性管道：retrieve/rerank 在 agent 之前执行（管道节点）
- agent 只负责接收 context + query，流式生成带 [n] 引用标注的回答
- system_prompt 通过 messages 动态注入（人设/范围每次不同）
- 支持 reasoning 模型（如 glm-4.6v-flash）：思考过程与正式回答分别流式输出
  通过 OpenAI SDK 直连流式，读取 delta.reasoning_content（DeepSeek/LM Studio 扩展字段）
- 启动时判断模型是否支持思考，据此调整 max_tokens：
  思考模型需要更大 token 预算（思考过程 + 正式回答），否则思考占满 token 导致 content 为空
"""
from collections.abc import AsyncIterator
from typing import Literal

from openai import AsyncOpenAI

from app.config import get_settings
from app.core.logging import get_logger
from app.services.llm.prompt import build_system_prompt

logger = get_logger("rag.agent")

#: 流式片段类型 — reasoning 为思考过程，content 为正式回答
StreamChunk = tuple[Literal["reasoning", "content"], str]

#: 已知思考模型的关键词（小写匹配）。模型名包含任一即判定为思考模型。
#: - glm-4.6v / glm-4.5：智谱 GLM 思考系列
#: - deepseek-r1 / deepseek-reasoner：DeepSeek 思考系列
#: - qwq / qwen3-thinking：通义千问思考系列
#: - o1 / o3 / o4：OpenAI 思考系列
_REASONING_MODEL_KEYWORDS: tuple[str, ...] = (
    "glm-4.6",
    "glm-4.5",
    "deepseek-r1",
    "deepseek-reasoner",
    "qwq",
    "qwen3-thinking",
    "qwen3-reasoning",
    "-o1",
    "o1-",
    "-o3",
    "o3-",
    "-o4",
    "o4-",
    "reasoning",
)

#: 思考模型建议的最小 max_tokens（思考过程 + 正式回答）
_REASONING_MIN_MAX_TOKENS = 4096


def is_reasoning_model(model_name: str) -> bool:
    """根据模型名判断是否为思考模型（支持 reasoning_content 输出）。

    匹配规则：模型名（小写）包含 _REASONING_MODEL_KEYWORDS 中任一关键词。
    常见非思考模型（qwen2.5-instruct / llama3 / Mistral 等）不会命中。
    """
    name = (model_name or "").lower()
    return any(kw in name for kw in _REASONING_MODEL_KEYWORDS)


def detect_reasoning_enabled() -> bool:
    """根据 settings.llm_enable_reasoning 判断是否按思考模型处理。

    - "auto"：按 settings.llm_model 模型名自动推断
    - "on" / "true" / "1"：强制按思考模型处理
    - "off" / "false" / "0" / 其他：强制按非思考模型处理
    """
    settings = get_settings()
    flag = (settings.llm_enable_reasoning or "auto").lower().strip()
    if flag == "auto":
        return is_reasoning_model(settings.llm_model)
    return flag in ("on", "true", "1")


class RAGAgent:
    """LLM 流式生成封装。

    使用 OpenAI SDK 直连（而非 PydanticAI 的 stream_text），以支持 reasoning 模型
    的思考过程逐字流式输出。PydanticAI 的 stream_text 只返回 TextPart，
    丢弃 ThinkingPart；其内部事件流（_stream_response）对 reasoning 的处理不稳定。
    OpenAI SDK 直接读取 delta.reasoning_content，兼容 LM Studio / DeepSeek 等。
    """

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        # 启动时一次性判断并缓存，避免每次调用重复推断
        self._reasoning_enabled: bool | None = None

    def _get_client(self) -> AsyncOpenAI:
        """懒加载 AsyncOpenAI 客户端单例。"""
        if self._client is None:
            settings = get_settings()
            self._client = AsyncOpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                timeout=settings.llm_request_timeout,
            )
            logger.info(
                "rag_client_created",
                base_url=settings.llm_base_url,
                model=settings.llm_model,
            )
        return self._client

    def _is_reasoning_enabled(self) -> bool:
        """判断当前模型是否按思考模型处理（缓存结果）。"""
        if self._reasoning_enabled is None:
            self._reasoning_enabled = detect_reasoning_enabled()
            settings = get_settings()
            logger.info(
                "reasoning_mode_detected",
                model=settings.llm_model,
                flag=settings.llm_enable_reasoning,
                reasoning_enabled=self._reasoning_enabled,
            )
        return self._reasoning_enabled

    def _resolve_max_tokens(self) -> int:
        """根据是否思考模型返回 max_tokens。

        思考模型需要更大预算（思考过程 + 正式回答），若配置值不足则提升到建议下限。
        非思考模型直接用配置值。
        """
        settings = get_settings()
        configured = settings.llm_max_tokens
        if self._is_reasoning_enabled() and configured < _REASONING_MIN_MAX_TOKENS:
            logger.warning(
                "max_tokens_boosted",
                model=settings.llm_model,
                old=configured,
                new=_REASONING_MIN_MAX_TOKENS,
                reason="思考模型需要更大 token 预算，否则思考过程占满导致正式回答为空",
            )
            return _REASONING_MIN_MAX_TOKENS
        return configured

    async def stream_answer(
        self,
        query: str,
        context: str,
        persona_name: str = "",
        persona_system_prompt: str = "",
        scope_type: str = "global",
        scope_ref: str = "",
    ) -> AsyncIterator[StreamChunk]:
        """流式生成回答，区分思考过程与正式回答。

        reasoning 模型（如 glm-4.6v-flash）会先输出 reasoning_content（思考），
        再输出 content（正式回答）；非 reasoning 模型只输出 content。

        Args:
            query: 用户问题
            context: 检索到的上下文（已由 context_builder 组装）
            persona_name: 人设名称
            persona_system_prompt: 人设系统提示词
            scope_type: global | channel | article
            scope_ref: channel slug 或 article slug

        Yields:
            (kind, delta) 元组，kind 为 "reasoning" 或 "content"
        """
        from datetime import date

        settings = get_settings()
        client = self._get_client()
        reasoning_enabled = self._is_reasoning_enabled()
        max_tokens = self._resolve_max_tokens()
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
            reasoning_enabled=reasoning_enabled,
            max_tokens=max_tokens,
        )

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.llm_temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # reasoning_content：DeepSeek / LM Studio reasoning 模型的扩展字段
            # 非思考模型该字段为 None，自动跳过
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield "reasoning", reasoning
            # content：正式回答
            if delta.content:
                yield "content", delta.content


# 单例
rag_agent = RAGAgent()
