"""测试 schemas/common.py 的 envelope / error_envelope。"""
from app.schemas.common import Envelope, Page, envelope, error_envelope


def test_envelope_ok():
    """默认 envelope {code:0, data:None, message:ok}。"""
    e = envelope({"foo": 1})
    assert e == {"code": 0, "data": {"foo": 1}, "message": "ok"}


def test_envelope_custom_message():
    """自定义 message。"""
    e = envelope(None, message="created")
    assert e["message"] == "created"
    assert e["code"] == 0


def test_error_envelope():
    """error_envelope 默认 code=-1。"""
    e = error_envelope("not found")
    assert e["code"] == -1
    assert e["data"] is None
    assert e["message"] == "not found"


def test_error_envelope_custom_code():
    """自定义 code。"""
    e = error_envelope("conflict", code=4090)
    assert e["code"] == 4090


def test_envelope_model():
    """Envelope[T] 模型序列化。"""
    e = Envelope[int](code=0, data=42, message="ok")
    assert e.data == 42
    assert e.model_dump() == {"code": 0, "data": 42, "message": "ok"}


def test_page_model():
    """Page[T] 分页模型。"""
    p = Page[int](items=[1, 2, 3], total=3, page=1, size=20)
    assert p.items == [1, 2, 3]
    assert p.total == 3
    assert p.page == 1
    assert p.size == 20
