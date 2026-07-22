"""测试 core/security.py：密码哈希 + JWT。"""
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    """argon2 哈希与校验。"""
    plain = "super-secret-123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_verify_password_invalid_hash():
    """无效哈希返回 False（不抛异常）。"""
    assert verify_password("any", "not-a-valid-hash") is False


def test_create_and_decode_access_token():
    """JWT 签发与解码往返。"""
    token = create_access_token("admin-001", extra={"username": "alice"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin-001"
    assert payload["username"] == "alice"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_invalid_token():
    """无效 JWT 返回 None。"""
    assert decode_access_token("not-a-jwt") is None
    assert decode_access_token("") is None
