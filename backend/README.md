# InkGrid Backend

> InkGrid 后端 —— FastAPI + RAG + 语音 + 政策采集。

骨架阶段，结构与依赖已就绪，业务实现按 P0–P4 推进。详见 [../plan/后端设计方案.md](../plan/后端设计方案.md)。

## 技术栈

| 层 | 选型 |
|----|------|
| Web 框架 | FastAPI 0.110+ (async) |
| ORM | SQLAlchemy 2.x (async) |
| 数据库 | PostgreSQL 16 |
| 缓存/限流 | Redis 7 |
| 向量库 | Milvus 2.4+ |
| Embedding | BGE-M3 |
| Reranker | bge-reranker-v2-m3 |
| LLM | 通义 / DeepSeek |
| 全文搜索 | Meilisearch 1.6+ |
| 任务队列 | Celery + Redis |
| 对象存储 | MinIO（本地）/ OSS（云） |
| 语音 | 流式 ASR / TTS / silero-vad |

## 目录结构

```
backend/
├── app/
│   ├── api/              # 路由层（public / admin / ws）
│   ├── core/             # 鉴权、限流、日志、错误、合规
│   ├── models/           # SQLAlchemy ORM
│   ├── schemas/          # Pydantic 请求/响应
│   ├── crud/             # 数据访问层
│   ├── services/         # 业务逻辑（cms / rag / llm / voice / search / storage）
│   ├── ingest/           # 自动入库管道
│   ├── collector/        # 政策采集管道
│   ├── tasks/            # Celery 任务
│   ├── db/               # 基础设施连接
│   └── utils/            # 通用工具
├── alembic/              # 数据库迁移
├── tests/                # 测试（镜像 app 结构）
├── scripts/              # 运维脚本
├── docker/               # Dockerfile + compose
├── alembic.ini
├── pyproject.toml
└── .env.example
```

## 快速开始

> 要求 Python ≥ 3.11（推荐 3.12+）。开发期用精简 dev 栈，不含 Milvus / Meilisearch（P2 接入 RAG 时再起全套）。

### 1. 安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"          # P0 核心依赖
# pip install -e ".[dev,rag]"    # P2+ 接入 RAG 时加装向量库/Embedding 等
```

### 2. 启动基础设施（Docker 精简 dev 栈）

```bash
docker compose -f docker/docker-compose.dev.yml up -d
docker compose -f docker/docker-compose.dev.yml ps     # 确认 healthy
```

启动 Postgres + Redis + MinIO，并自动初始化 `inkgrid` bucket 为公开读。

### 3. 配置环境变量

```bash
cp .env.example .env
# DEBUG=true 已默认开启（开发期 cookie 不强制 Secure）
# 按需修改 DATABASE_URL / REDIS_URL / MINIO_* 等
```

### 4. 初始化数据库

```bash
# 方式 A：开发期直接建表（含种子数据：默认人设/频道/站点设置）
python scripts/init_db.py

# 方式 B：生产用 Alembic 迁移
alembic upgrade head
python scripts/init_db.py    # 仅写种子数据（表已存在会跳过）

# 创建博主账号（已存在则重置密码）
python scripts/create_admin.py admin yourpassword
```

### 5. 启动服务

```bash
# Web 进程（开发热重载）
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 另开终端：Celery worker（入库任务）
celery -A app.tasks.celery_app worker -l info

# 另开终端：Celery beat（定时任务，P1+ 用）
celery -A app.tasks.celery_app beat -l info
```

### 6. 验证

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# API 文档（DEBUG=true 时开放）
# 浏览器打开 http://127.0.0.1:8000/docs
```

### 7. 一键启动全栈（含 Milvus / Meilisearch，P2+ 用）

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | Web / WS / docs |
| PostgreSQL | 5432 | 主库（用户/密码/库名均 `inkgrid`）|
| Redis | 6379 | 限流 + Celery broker |
| MinIO S3 API | 9000 | 对象存储 |
| MinIO Console | 9001 | 浏览器管理（账号 `minio` / 密码 `minio123`）|
| Milvus | 19530 | 向量库（仅全栈）|
| Meilisearch | 7700 | 全文搜索（仅全栈）|

### 停止与清理

```bash
# 停止 dev 栈（保留数据）
docker compose -f docker/docker-compose.dev.yml down

# 停止并删除数据卷（彻底重置）
docker compose -f docker/docker-compose.dev.yml down -v
```

## 开发命令

```bash
# 测试
pytest

# Lint
ruff check .
ruff format .

# 类型检查
mypy app

# 数据库迁移
alembic revision --autogenerate -m "add xxx table"
alembic upgrade head
```

## 分层约定

| 层 | 职责 | 禁止 |
|----|------|------|
| `api/` | 参数校验、调 service、返回 envelope | 直接操作 DB |
| `crud/` | 纯 DB 操作 | 调 service / 外部依赖 |
| `services/` | 业务编排 | 直接处理 HTTP 请求 |
| `tasks/` | Celery 任务，调 services/ingest/collector | 写业务逻辑 |
| `core/` | 横切关注点 | 含业务逻辑 |

## 关联文档

- [后端设计方案](../plan/后端设计方案.md)
- [产品与技术方案](../plan/产品与技术方案.md)
- [前端模块设计文档](../plan/前端模块设计文档.md)
