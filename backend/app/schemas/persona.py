"""人设请求/响应 schema。"""
from pydantic import BaseModel, ConfigDict


class PersonaBase(BaseModel):
    serial: str
    name: str
    tagline: str
    description: str
    tags: list[str] | None = None
    avatar: str | None = None


class PersonaCreate(PersonaBase):
    system_prompt: str
    scope: str = "global"


class PersonaUpdate(BaseModel):
    serial: str | None = None
    name: str | None = None
    tagline: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    avatar: str | None = None
    system_prompt: str | None = None
    scope: str | None = None


class Persona(PersonaBase):
    """公开响应（不含 system_prompt）。与前端 Persona 类型对齐。"""

    model_config = ConfigDict(from_attributes=True)

    id: str


class PersonaAdmin(Persona):
    """后台响应（含 system_prompt）。"""

    system_prompt: str
    scope: str
