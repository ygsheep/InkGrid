"""测试 core/errors.py：异常体系与 envelope 转换。"""
from app.core.errors import (
    AppError,
    AuthError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    to_envelope,
)


def test_app_error_defaults():
    """AppError 默认值。"""
    e = AppError()
    assert e.status_code == 400
    assert e.code == -1
    assert e.message == "请求失败"
    assert e.data is None


def test_app_error_custom_message():
    """自定义 message。"""
    e = AppError("custom")
    assert e.message == "custom"


def test_not_found_error():
    """NotFoundError 404/4040。"""
    e = NotFoundError()
    assert e.status_code == 404
    assert e.code == 4040
    assert e.message == "资源不存在"


def test_conflict_error():
    """ConflictError 409/4090。"""
    e = ConflictError()
    assert e.status_code == 409
    assert e.code == 4090


def test_auth_error():
    """AuthError 401/4010。"""
    e = AuthError()
    assert e.status_code == 401
    assert e.code == 4010


def test_forbidden_error():
    """ForbiddenError 403/4030。"""
    e = ForbiddenError()
    assert e.status_code == 403
    assert e.code == 4030


def test_rate_limit_error_with_data():
    """RateLimitError 含 reset_at / remaining。"""
    e = RateLimitError("限流", reset_at="2026-01-01T00:00:00+00:00", remaining=3)
    assert e.status_code == 429
    assert e.code == 4290
    assert e.data == {"reset_at": "2026-01-01T00:00:00+00:00", "remaining": 3}


def test_validation_error():
    """ValidationError 422/4220。"""
    e = ValidationError()
    assert e.status_code == 422
    assert e.code == 4220


def test_to_envelope():
    """异常转 envelope dict。"""
    e = NotFoundError("文章不存在")
    env = to_envelope(e)
    assert env == {
        "code": 4040,
        "data": None,
        "message": "文章不存在",
    }


def_to_envelope_with_data = None


def test_to_envelope_with_data():
    """带 data 的异常转 envelope。"""
    e = RateLimitError(reset_at="2026-01-01", remaining=5)
    env = to_envelope(e)
    assert env["data"] == {"reset_at": "2026-01-01", "remaining": 5}
    assert env["code"] == 4290
