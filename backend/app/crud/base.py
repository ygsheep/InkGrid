"""泛型 CRUD 基类：list / get / create / update / delete。

约定：
- 所有方法接收 AsyncSession，由调用方管理事务与生命周期
- 仅做纯 DB 操作，不调用 service 或外部依赖
- 返回 ORM 模型实例，由 schema 层通过 from_attributes=True 转换为 DTO
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """泛型 CRUD 基类。子类设置 model 即可复用基础方法。"""

    model: type[ModelT]

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id_: Any) -> ModelT | None:
        """按主键取一条。"""
        return await db.get(self.model, id_)

    async def list(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ModelT]:
        """基础分页列表（无筛选）。子类一般重写以加筛选与排序。"""
        stmt = select(self.model).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: CreateSchemaT) -> ModelT:
        """新建。调用方负责 commit。"""
        data = obj_in.model_dump(exclude_unset=True)
        db_obj = self.model(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelT,
        obj_in: UpdateSchemaT | dict,
    ) -> ModelT:
        """按 schema/dict 更新已加载的对象。调用方负责 commit。"""
        if isinstance(obj_in, BaseModel):
            data = obj_in.model_dump(exclude_unset=True)
        else:
            data = {k: v for k, v in obj_in.items() if v is not None}
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, db_obj: ModelT) -> None:
        """删除已加载的对象。调用方负责 commit。"""
        await db.delete(db_obj)
        await db.flush()
