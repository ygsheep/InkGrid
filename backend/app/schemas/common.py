"""统一响应 envelope、分页结构。"""
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """统一响应包装：{ code, data, message }。"""

    code: int = 0
    data: T | None = None
    message: str = "ok"


class Pagination(BaseModel):
    """分页元信息。"""

    page: int
    size: int
    total: int


class Page(BaseModel, Generic[T]):
    """分页响应：{ items, total, page, size }。"""

    items: Sequence[T]
    total: int
    page: int
    size: int


def envelope(data, message: str = "ok", code: int = 0) -> dict:
    """构造响应 envelope。"""
    return {"code": code, "data": data, "message": message}


def error_envelope(message: str, code: int = -1) -> dict:
    """构造错误响应。"""
    return {"code": code, "data": None, "message": message}
