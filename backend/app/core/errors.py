"""统一异常体系 → envelope {code, data, message}。

使用方式：
- service / api 层 raise 业务异常
- FastAPI 在 main.py 注册 exception_handler 把异常转为 envelope
- envelope.error_code 与 HTTP 状态码映射
"""
from typing import Any


class AppError(Exception):
    """业务异常基类。"""

    #: HTTP 状态码
    status_code: int = 400
    #: envelope.code（业务码，0=成功，负数=失败）
    code: int = -1
    #: 给前端展示的消息
    message: str = "请求失败"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: int | None = None,
        status_code: int | None = None,
        data: Any | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.data = data
        super().__init__(self.message)


class NotFoundError(AppError):
    """资源不存在。"""

    status_code = 404
    code = 4040
    message = "资源不存在"


class ConflictError(AppError):
    """唯一约束冲突。"""

    status_code = 409
    code = 4090
    message = "资源已存在"


class AuthError(AppError):
    """未登录或 token 无效。"""

    status_code = 401
    code = 4010
    message = "未登录"


class ForbiddenError(AppError):
    """无权限。"""

    status_code = 403
    code = 4030
    message = "无权限"


class RateLimitError(AppError):
    """限流触发。"""

    status_code = 429
    code = 4290
    message = "请求过于频繁"

    def __init__(
        self,
        message: str | None = None,
        *,
        reset_at: str | None = None,
        remaining: int = 0,
    ) -> None:
        super().__init__(message)
        self.data = {"reset_at": reset_at, "remaining": remaining}


class ValidationError(AppError):
    """业务校验失败（区别于 Pydantic 校验）。"""

    status_code = 422
    code = 4220
    message = "参数校验失败"


def to_envelope(err: AppError) -> dict:
    """把异常转为 envelope dict。"""
    return {
        "code": err.code,
        "data": err.data,
        "message": err.message,
    }
