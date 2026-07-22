"""后台鉴权 schema。"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录入参。"""

    username: str
    password: str


class AdminInfo(BaseModel):
    """博主信息（me 接口返回）。"""

    id: str
    username: str
