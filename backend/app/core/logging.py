"""structlog 配置 + request_id 上下文。

- 输出 JSON 结构化日志
- 全部请求经 middleware 注入 request_id，贯穿日志 + WS 帧
- 提供 get_request_id() 给其他模块使用
"""
import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

#: 当前请求的 request_id（每请求隔离）
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def _add_request_id(_, __, event_dict: dict) -> dict:
    """processor：把 request_id 注入到每条日志。"""
    rid = request_id_var.get("")
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(debug: bool = False) -> None:
    """初始化 structlog 与标准 logging。

    应在应用启动时调用一次。
    """
    level = logging.DEBUG if debug else logging.INFO

    # 标准库 logging 重定向到 structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    """获取 logger。"""
    return structlog.get_logger(name)


def new_request_id() -> str:
    """生成新 request_id 并写入上下文。返回 id 字符串。"""
    rid = uuid.uuid4().hex
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """读取当前上下文 request_id。"""
    return request_id_var.get("")
