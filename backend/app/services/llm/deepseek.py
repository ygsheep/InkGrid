"""DeepSeek provider。"""
from app.services.llm.base import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek（OpenAI 兼容 API）provider。

    base_url 固定为 https://api.deepseek.com/v1，
    其余配置（api_key / model / temperature / max_tokens / timeout）
    继承自基类，默认取自 ``app.config.Settings``。
    """

    base_url = "https://api.deepseek.com/v1"
