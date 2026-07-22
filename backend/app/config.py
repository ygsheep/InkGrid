"""应用配置：基于 Pydantic BaseSettings，从环境变量加载。"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。所有值优先来自环境变量，缺省值用于本地开发。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===== 应用 =====
    app_name: str = "InkGrid"
    debug: bool = False
    api_prefix: str = "/api"

    # ===== 数据库 =====
    database_url: str = "postgresql+asyncpg://inkgrid:inkgrid@localhost:5432/inkgrid"

    # ===== Redis =====
    redis_url: str = "redis://localhost:6379/0"

    # ===== 站点 =====
    site_name: str = "inkgrid.dev"
    site_author: str = "张三"
    site_version: str = "v1.0.0"

    # ===== 鉴权 =====
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    cookie_name: str = "admin_token"

    # ===== 限流 =====
    rate_limit_ip_per_min: int = 60
    rate_limit_chat_ip_per_min: int = 20
    rate_limit_chat_anon_per_day: int = 50

    # ===== Next.js revalidate =====
    next_revalidate_token: str = ""
    next_public_api_base: str = "http://localhost:3000"

    # ===== 对象存储（MinIO） =====
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "inkgrid"
    minio_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    """单例配置，避免重复读取环境变量。"""
    return Settings()
