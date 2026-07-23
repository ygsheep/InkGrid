"""LLM provider 抽象基类 + 流式接口。"""
from __future__ import annotations

from openai import AsyncOpenAI
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger("llm.base")


class LLMError(AppError):
    """LLM 调用或配置异常。"""

    status_code = 502
    code = 5020
    message = "LLM 调用失败"


class BaseLLMProvider:
    """LLM provider 抽象基类。

    封装 OpenAI 兼容客户端（AsyncOpenAI），并产出 PydanticAI 可用的 Model 实例。
    子类通过覆盖 ``base_url`` 类属性指定各自的 OpenAI 兼容入口；
    其余配置（api_key / model / temperature / max_tokens / timeout）
    默认取自 ``app.config.Settings``，也可在实例化时显式覆盖。

    对于 ``lmstudio`` 等本地兼容服务，可直接实例化本基类，使用 settings 中的 base_url。
    """

    #: OpenAI 兼容 API base_url，子类覆盖；空串表示回退到 settings.llm_base_url
    base_url: str = ""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or self.base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.temperature = (
            temperature if temperature is not None else settings.llm_temperature
        )
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        self.timeout = timeout if timeout is not None else settings.llm_request_timeout

    def create_client(self) -> AsyncOpenAI:
        """构造 AsyncOpenAI 客户端（含连接 / 读取超时）。"""
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def create_streaming_model(self) -> Model:
        """构造 PydanticAI 的 OpenAIChatModel（流式可用）。

        - 通过 ``OpenAIProvider(openai_client=...)`` 注入预配置的 AsyncOpenAI，
          统一管控 base_url / api_key / timeout。
        - temperature / max_tokens 经 ``ModelSettings`` 注入模型，使返回的 Model
          自带采样参数，调用方（Agent 层）无需再传。
        """
        client = self.create_client()
        provider = OpenAIProvider(openai_client=client)
        model_settings = ModelSettings(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        logger.info(
            "build_llm_model",
            provider=self.__class__.__name__,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return OpenAIChatModel(
            model_name=self.model,
            provider=provider,
            settings=model_settings,
        )


def build_llm_model(provider: str | None = None) -> Model:
    """根据 ``settings.llm_provider`` 构造对应的 PydanticAI Model。

    Args:
        provider: 显式指定 provider 名（lmstudio | qwen | deepseek）；
            为 None 时读取 ``settings.llm_provider``。

    Returns:
        PydanticAI Model 实例，可直接传给 ``Agent(model=...)``。

    Raises:
        LLMError: 未知的 provider 名。
    """
    name = (provider or get_settings().llm_provider).lower().strip()

    # 延迟导入，避免 base 模块 import 即拉起子 provider
    if name == "qwen":
        from app.services.llm.qwen import QwenProvider

        return QwenProvider().create_streaming_model()
    if name == "deepseek":
        from app.services.llm.deepseek import DeepSeekProvider

        return DeepSeekProvider().create_streaming_model()
    if name == "lmstudio":
        return BaseLLMProvider().create_streaming_model()

    raise LLMError(message=f"未知 llm_provider: {name}")
