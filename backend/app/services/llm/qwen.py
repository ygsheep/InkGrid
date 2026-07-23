"""通义千问 provider。"""
from app.services.llm.base import BaseLLMProvider


class QwenProvider(BaseLLMProvider):
    """通义千问（DashScope OpenAI 兼容模式）provider。

    base_url 固定为 https://dashscope.aliyuncs.com/compatible-mode/v1，
    其余配置（api_key / model / temperature / max_tokens / timeout）
    继承自基类，默认取自 ``app.config.Settings``。
    """

    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
