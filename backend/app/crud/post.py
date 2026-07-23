"""文章 CRUD。

- 公开列表只看 status='published'，支持 channel(slug)/tag/q 筛选
- 后台列表可看所有状态，支持 status 筛选
- 详情含 channel 关联，需 selectinload 预加载
"""
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.channel import Channel
from app.models.post import Post
from app.schemas.post import PostCreate, PostUpdate


class CRUDPost(CRUDBase[Post, PostCreate, PostUpdate]):
    """文章数据访问层。"""

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
        *,
        only_published: bool = False,
    ) -> Post | None:
        """按 slug 取文章（含 channel）。"""
        stmt = (
            select(Post)
            .options(selectinload(Post.channel))
            .where(Post.slug == slug)
        )
        if only_published:
            stmt = stmt.where(Post.status == "published")
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_channel(
        self,
        db: AsyncSession,
        post_id: UUID,
    ) -> Post | None:
        """按 id 取文章（含 channel 预加载）。用于后台详情。"""
        stmt = (
            select(Post)
            .options(selectinload(Post.channel))
            .where(Post.id == post_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_published(
        self,
        db: AsyncSession,
        *,
        channel: str | None = None,
        tag: str | None = None,
        q: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Post], int]:
        """公开文章列表：仅 published，按 published_at desc。

        - channel: 频道 slug
        - tag: 任意 tag 命中
        - q: title/excerpt 模糊匹配
        返回 (items, total)
        """
        stmt = (
            select(Post)
            .options(selectinload(Post.channel))
            .where(Post.status == "published")
        )
        count_stmt = select(func.count()).select_from(Post).where(
            Post.status == "published"
        )
        if channel:
            stmt = stmt.join(Channel).where(Channel.slug == channel)
            count_stmt = count_stmt.join(Channel).where(Channel.slug == channel)
        if tag:
            stmt = stmt.where(Post.tags.any(tag))  # type: ignore[attr-defined]
            count_stmt = count_stmt.where(Post.tags.any(tag))  # type: ignore[attr-defined]
        if q:
            like = f"%{q}%"
            cond = or_(Post.title.ilike(like), Post.excerpt.ilike(like))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Post.published_at.desc().nullslast()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())

        total = (await db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_admin(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        channel_id: UUID | None = None,
        q: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Post], int]:
        """后台文章列表：可看所有状态。"""
        stmt = select(Post).options(selectinload(Post.channel))
        count_stmt = select(func.count()).select_from(Post)
        if status:
            stmt = stmt.where(Post.status == status)
            count_stmt = count_stmt.where(Post.status == status)
        if channel_id:
            stmt = stmt.where(Post.channel_id == channel_id)
            count_stmt = count_stmt.where(Post.channel_id == channel_id)
        if q:
            like = f"%{q}%"
            cond = or_(Post.title.ilike(like), Post.excerpt.ilike(like))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Post.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())
        total = (await db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_by_channel_slug(
        self,
        db: AsyncSession,
        slug: str,
        *,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Post], int]:
        """按频道 slug 列出已发布文章(可按标签筛选)。"""
        return await self.list_published(
            db, channel=slug, tag=tag, offset=offset, limit=limit
        )

    async def set_status(
        self,
        db: AsyncSession,
        db_obj: Post,
        status: str,
    ) -> Post:
        """切换状态。发布时自动填 published_at（仅首次）。"""
        from datetime import datetime, timezone

        db_obj.status = status
        if status == "published" and db_obj.published_at is None:
            db_obj.published_at = datetime.now(timezone.utc)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


post = CRUDPost(Post)
