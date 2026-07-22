"""创建博主账号。

用法：
    python -m scripts.create_admin <username> <password>
    或：python scripts/create_admin.py admin mypassword
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.models.admin import Admin  # noqa: E402

logger = get_logger("scripts.create_admin")


async def create_admin(username: str, password: str) -> str:
    """创建博主账号。已存在则更新密码。"""
    async with async_session_factory() as db:
        existing = (
            await db.execute(select(Admin).where(Admin.username == username))
        ).scalar_one_or_none()
        if existing:
            existing.password_hash = hash_password(password)
            await db.commit()
            logger.info("admin_password_reset", username=username)
            return str(existing.id)

        admin = Admin(
            username=username,
            password_hash=hash_password(password),
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        logger.info("admin_created", username=username, admin_id=str(admin.id))
        return str(admin.id)


async def main() -> None:
    configure_logging()
    if len(sys.argv) < 3:
        print("用法：python scripts/create_admin.py <username> <password>")
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    if len(password) < 6:
        print("密码至少 6 位")
        sys.exit(1)
    admin_id = await create_admin(username, password)
    print(f"admin created: id={admin_id} username={username}")


if __name__ == "__main__":
    asyncio.run(main())
