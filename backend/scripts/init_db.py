"""初始化数据库表 + 种子数据。

用法：
    python -m scripts.init_db
    或：python scripts/init_db.py

流程：
1. 用 Base.metadata.create_all 创建所有表（开发期简化，生产用 alembic upgrade head）
2. 写入种子数据：默认频道、默认人设、站点设置单行
3. 幂等：已存在的数据跳过
"""
import asyncio
import sys
from pathlib import Path

# 允许直接 `python scripts/init_db.py` 运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.db.session import async_session_factory, engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.channel import Channel  # noqa: E402
from app.models.persona import Persona  # noqa: E402
from app.models.settings import SiteSettings  # noqa: E402

logger = get_logger("scripts.init_db")


async def create_tables() -> None:
    """创建所有表（开发期用，生产走 alembic）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("tables_created")


async def seed_data() -> None:
    """写入种子数据：默认人设、默认频道、站点设置。"""
    async with async_session_factory() as db:
        # 默认人设
        persona_exists = (
            await db.execute(select(Persona).where(Persona.serial == "001"))
        ).scalar_one_or_none()
        if not persona_exists:
            persona = Persona(
                serial="001",
                name="InkGrid 助手",
                tagline="文章知识库问答助手",
                description="基于站点已发布的文章为你答疑。",
                tags=["默认", "通用"],
                system_prompt=(
                    "你是 InkGrid 站点的问答助手。"
                    "请基于提供的文章片段回答用户问题，"
                    "若信息不足请如实说明，不要编造。"
                    "回答需简洁、准确，并在末尾标注引用来源。"
                ),
                scope="global",
            )
            db.add(persona)
            await db.flush()
            logger.info("seed_persona_created", persona_id=str(persona.id))
            persona_id = persona.id
        else:
            persona_id = persona_exists.id
            logger.info("seed_persona_exists", persona_id=str(persona_id))

        # 默认频道
        channel_exists = (
            await db.execute(select(Channel).where(Channel.slug == "blog"))
        ).scalar_one_or_none()
        if not channel_exists:
            channel = Channel(
                slug="blog",
                name="博客",
                description="技术博客文章",
                accent="channel",
                persona_id=persona_id,
            )
            db.add(channel)
            logger.info("seed_channel_created", slug="blog")
        else:
            logger.info("seed_channel_exists", slug="blog")

        # 站点设置
        settings_exists = (
            await db.execute(select(SiteSettings).where(SiteSettings.id == 1))
        ).scalar_one_or_none()
        if not settings_exists:
            s = SiteSettings(
                id=1,
                site_name="InkGrid",
                author="博主",
                version="v1.0.0",
                extra={},
            )
            db.add(s)
            logger.info("seed_settings_created")
        else:
            logger.info("seed_settings_exists")

        await db.commit()


async def main() -> None:
    configure_logging()
    logger.info("init_db_start")
    await create_tables()
    await seed_data()
    logger.info("init_db_done")


if __name__ == "__main__":
    asyncio.run(main())
