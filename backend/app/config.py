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

    # ===== CORS 额外 origin =====
    # 局域网联调时填开发机 IP,如 "http://192.168.1.37:3000";多个用逗号分隔。
    # 默认空,不影响现有 localhost 开发。
    cors_extra_origins: str = ""

    # ===== 对象存储（MinIO） =====
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "inkgrid"
    minio_secure: bool = False

    # ===== LLM 网关（OpenAI 兼容） =====
    # 开发期：LMStudio 本地服务 http://localhost:1234/v1，API Key 任意值
    # 生产期：通义 https://dashscope.aliyuncs.com/compatible-mode/v1
    #         DeepSeek https://api.deepseek.com/v1
    llm_provider: str = "lmstudio"  # lmstudio | qwen | deepseek
    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = "lm-studio"
    llm_model: str = "qwen2.5-7b-instruct"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_request_timeout: float = 60.0  # 流式首 token 超时阈值
    # 思考模式：auto（按模型名自动推断）/ on（强制按思考模型处理）/ off（强制按非思考模型处理）
    # 思考模型（glm-4.6v/deepseek-r1/qwq 等）会先输出 reasoning_content 再输出 content，
    # 需要更大的 max_tokens，否则思考过程占满 token 导致正式回答为空。
    llm_enable_reasoning: str = "auto"

    # ===== Embedding（BGE-M3） =====
    # 双模式：配了 embedding_tei_url 用 TEI 服务，否则进程内 sentence-transformers 加载
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"  # cpu | cuda | mps（仅进程内模式）
    embedding_cache_dir: str = "./models"  # HuggingFace 模型缓存目录
    embedding_batch_size: int = 16
    embedding_tei_url: str = ""  # TEI 服务地址，如 http://localhost:8080；空则进程内

    # ===== Reranker（bge-reranker-v2-m3） =====
    # 双模式：配了 reranker_tei_url 用 TEI 服务，否则进程内 sentence-transformers 加载
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"  # cpu | cuda | mps（仅进程内模式）
    reranker_cache_dir: str = "./models"
    reranker_top_n: int = 5  # 精排后保留数量
    reranker_tei_url: str = ""  # TEI 服务地址，如 http://localhost:8081；空则进程内
    # 澄清阈值：rerank top 分数低于此值时触发澄清引导（不调 LLM，直接让用户换问法）。
    # bge-reranker-v2-m3 对中文查询打分偏低，0.3 过严会误杀正常查询，默认 0.1。
    # 调高→更保守（更多查询被判为"不相关"）；调低→更宽松（几乎都走 LLM）。
    rag_clarify_threshold: float = 0.1

    # ===== Milvus 向量库 =====
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "inkgrid_chunks"
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_use_partition: bool = True  # 启用三级范围 partition 路由

    # ===== Meilisearch 全文搜索 =====
    # 仅索引 status=published 的文章，供前端即时搜索
    meili_host: str = "localhost"
    meili_port: int = 7700
    meili_key: str = ""  # 开发可空；生产用 master key
    meili_posts_index: str = "posts"
    meili_enabled: bool = True  # False 时搜索接口返回空，不阻断启动


@lru_cache
def get_settings() -> Settings:
    """单例配置，避免重复读取环境变量。"""
    return Settings()
