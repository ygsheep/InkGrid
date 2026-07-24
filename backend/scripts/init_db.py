"""初始化数据库表 + 种子数据。

用法：
    python -m scripts.init_db
    或：python scripts/init_db.py

流程：
1. 用 Base.metadata.create_all 创建所有表（开发期简化，生产用 alembic upgrade head）
2. 修补已存在表的结构差异（create_all 对已存在的表不会修改列定义）
3. 写入种子数据：默认人设、站点设置单行
4. 幂等：已存在的数据跳过

注：频道由用户在后台自行创建（文章即知识库，按知识域组织频道）。
    博主账号请用 scripts/create_admin.py 单独创建。
"""
import asyncio
import sys
from pathlib import Path

# 允许直接 `python scripts/init_db.py` 运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text  # noqa: E402

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.db.session import async_session_factory, engine  # noqa: E402
from app.models import Base  # noqa: E402  触发所有模型注册到 metadata
from app.models.persona import Persona  # noqa: E402
from app.models.settings import SiteSettings  # noqa: E402

logger = get_logger("scripts.init_db")


# 已知结构修补清单：列必须为 TIMESTAMP WITH TIME ZONE。
# 历史问题：早期 ORM 漏配 timezone=True，create_all 建出了 WITHOUT TIME ZONE 列。
# create_all(checkfirst=True) 对已存在的表不会修改列定义，这里手动 ALTER 修补。
# 详见 alembic/versions/0003_fix_published_at_tz.py
_TIMEZONE_COLUMN_FIXES: list[tuple[str, str]] = [
    ("posts", "published_at"),
]

# 历史表新增列清单：(表, 列, DDL 类型定义)。
# 用于 ORM 模型新增字段后，给已存在的表补列（create_all 不会给已存在表加列）。
# 全新库由 create_all 建表时已包含这些列，此处幂等跳过。
_ADD_COLUMN_FIXES: list[tuple[str, str, str]] = [
    # knowledge_docs 多格式上传元数据（v2.2 知识库多格式上传）
    ("knowledge_docs", "original_filename", "VARCHAR(255)"),
    ("knowledge_docs", "source_format", "VARCHAR(20)"),
    ("knowledge_docs", "mime_type", "VARCHAR(100)"),
    ("knowledge_docs", "source_size", "BIGINT"),
]


async def _patch_timezone_columns() -> None:
    """幂等修补：把指定列转为 TIMESTAMP WITH TIME ZONE（仅当当前类型不含时区时）。"""
    async with engine.begin() as conn:
        for table, column in _TIMEZONE_COLUMN_FIXES:
            row = (
                await conn.execute(
                    text(
                        "SELECT data_type FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": column},
                )
            ).fetchone()
            if row is None:
                # 表或列不存在（全新库由 create_all 建立时已正确，无需 ALTER）
                continue
            if row[0] == "timestamp with time zone":
                continue
            logger.warning(
                "patching_timezone_column",
                table=table,
                column=column,
                old_type=row[0],
                new_type="timestamp with time zone",
            )
            # USING 让 PG 把 naive 当作 UTC 转为 timestamptz
            await conn.execute(
                text(
                    f"ALTER TABLE {table} ALTER COLUMN {column} "
                    f"TYPE TIMESTAMP WITH TIME ZONE "
                    f"USING {column} AT TIME ZONE 'UTC'"
                )
            )
            logger.info("patched_timezone_column", table=table, column=column)


async def _patch_added_columns() -> None:
    """幂等补列：给已存在的表新增 ORM 模型里后加的列。

    create_all(checkfirst=True) 不会给已存在的表加新列，这里用
    information_schema 探测，缺失才 ADD COLUMN（均允许 NULL，无需默认值）。
    """
    async with engine.begin() as conn:
        for table, column, ddl_type in _ADD_COLUMN_FIXES:
            row = (
                await conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": column},
                )
            ).fetchone()
            if row is not None:
                continue
            logger.warning(
                "adding_missing_column",
                table=table,
                column=column,
                ddl_type=ddl_type,
            )
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
            )
            logger.info("added_missing_column", table=table, column=column)


async def create_tables() -> None:
    """创建所有表（开发期用，生产走 alembic）。

    create_all 默认 checkfirst=True，已存在的表会跳过，幂等。
    表清单来源于 app.models 子模块注册到 Base.metadata 的 __tablename__。
    """
    table_names = sorted(Base.metadata.tables.keys())
    logger.info("tables_to_create", tables=table_names)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("tables_created", count=len(table_names))
    # 修补 create_all 无法处理的已存在表结构差异
    await _patch_timezone_columns()
    await _patch_added_columns()


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
