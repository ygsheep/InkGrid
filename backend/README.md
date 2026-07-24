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
├── scripts/              # 运维脚本（init_db / create_admin / download_models / convert_bge_m3 / smoke_rag 等）
├── models/               # 预下载的 HuggingFace 模型（bge-m3 / bge-reranker-v2-m3，挂载给 TEI）
├── docker/               # Dockerfile + compose
├── alembic.ini
├── pyproject.toml
└── .env.example
```

## Docker 部署（推荐）

按依赖顺序依次启动：**基础设施 → 任务队列 → Web**。所有命令在 `backend/` 下运行。

> 国内网络若拉取镜像失败，先配置 Docker 镜像加速（见[主 README](../README.md#0-前置配置镜像加速国内网络)）。

### 1. 基础搭建

```bash
# P0 精简栈：Postgres + Redis + MinIO
docker compose -f docker/docker-compose.dev.yml up -d postgres redis minio
docker compose -f docker/docker-compose.dev.yml ps    # 确认 healthy

# ═══ P1+ RAG 全栈（含 Milvus / TEI / etcd / Meilisearch）═══
# docker compose -f docker/docker-compose.dev.yml up -d
```

### 2. 任务队列

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d worker beat
```

### 3. 后端 Web

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d web
```

### 4. 环境变量 & 初始化

```bash
cd backend
cp .env.example .env
# 按需修改 DATABASE_URL / REDIS_URL / MINIO_* 等

# 建表 + 种子数据
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml exec web python scripts/init_db.py

# 创建管理员账号
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml exec web python scripts/create_admin.py admin yourpassword
```

### 5. 验证

```bash
curl http://localhost:8000/health
# 浏览器打开 http://localhost:8000/docs
```

### 6. 停止与清理

```bash
# 停止应用服务（保留数据）
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down

# 停止基础设施（保留数据）
docker compose -f docker/docker-compose.dev.yml down

# 停止并删除数据卷（彻底重置）
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down -v
docker compose -f docker/docker-compose.dev.yml down -v
```

### RAG 模型与配置

TEI 容器通过挂载 `backend/models/` 离线加载模型，首次部署需预下载。

```bash
cd backend

# 下载全部模型（bge-m3 ~4.3GB + bge-reranker-v2-m3 ~2.1GB）
python scripts/download_models.py

# 仅查看下载状态
python scripts/download_models.py --list

# 跳过 ONNX 文件（仅用 safetensors，省约 1.5GB）
python scripts/download_models.py --no-onnx
```

脚本特性：hf-mirror 加速 / 断点续传 / 文件过滤 / 下载后校验 / 幂等跳过。

> 若 bge-m3 下载到的是 `pytorch_model.bin` 而非 `model.safetensors`（TEI 1.5+ 只认 safetensors），需转换：`python scripts/convert_bge_m3.py`（需要 torch）。

#### Embedding / Reranker 双模式

| 模式 | 触发条件 | 说明 |
|------|---------|------|
| TEI 服务（推荐生产）| `.env` 配了 `EMBEDDING_TEI_URL` / `RERANKER_TEI_URL` | 走 HTTP 调 TEI 容器，无需本地 torch |
| 进程内推理（仅开发）| 上述 URL 留空 | sentence-transformers 加载本地模型，首次下载约 1.2GB |

TEI 容器启动后，`.env` 中保持 `EMBEDDING_TEI_URL=http://localhost:8080` 和 `RERANKER_TEI_URL=http://localhost:8081` 即可。

#### RAG 端到端冒烟测试

```bash
cd backend
python scripts/smoke_rag.py
# 验证：Milvus 连接 → TEI embedding → 入库 → 稠密检索 → TEI rerank
```

---

## 本地开发

> 要求 **Python ≥ 3.11**（推荐 3.12+；3.14 已验证可用）。
> P0 阶段只需核心依赖 + 精简 dev 栈（Postgres/Redis/MinIO）。
> P1+ 接入 RAG 需加装 `[rag]` extras + 下载 BGE 模型 + 启动 Milvus / TEI 服务。

### 1. 安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# P0 核心依赖（FastAPI / ORM / Celery / 鉴权 等）
pip install -e ".[dev]"
```

#### P1+ RAG 依赖（含 torch / pydantic-ai / pymilvus 等）

进程内 Embedding/Reranker 需要 torch。Windows / CPU 环境强烈建议用 PyTorch CPU index 安装：

```bash
# CPU 版 torch（推荐，国内镜像加速）
pip install -e ".[dev,rag]" \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple

# 或 TEI 服务模式（不装 torch，Embedding/Reranker 走 HTTP 调 TEI 容器）
pip install -e ".[dev,rag]" --extra-index-url https://pypi.org/simple
```

> 注意：extras 名是 `rag`（无点前缀）。正确写法 `".[rag]"`，不是 `".[.rag]"`。

### 2. 启动基础设施

```bash
docker compose -f docker/docker-compose.dev.yml up -d postgres redis minio
docker compose -f docker/docker-compose.dev.yml ps     # 确认 healthy
```

### 3. 配置环境变量

```bash
cp .env.example .env
# DEBUG=true 已默认开启（开发期 cookie 不强制 Secure）
# 按需修改 DATABASE_URL / REDIS_URL / MINIO_* 等
```

### 4. 初始化数据库

```bash
# 方式 A：开发期直接建表（含种子数据）
python scripts/init_db.py

# 方式 B：生产用 Alembic 迁移
alembic upgrade head
python scripts/init_db.py    # 仅写种子数据（表已存在会跳过）

# 创建博主账号
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
curl http://127.0.0.1:8000/health
# 浏览器打开 http://127.0.0.1:8000/docs
```

---

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | Web / WS / docs |
| PostgreSQL | 5432 | 主库（用户/密码/库名均 `inkgrid`）|
| Redis | 6379 | 限流 + Celery broker |
| MinIO S3 API | 9000 | 对象存储 |
| MinIO Console | 9001 | 浏览器管理（账号 `minio` / 密码 `minio123`）|
| Milvus | 19530 | 向量库（仅全栈）|
| TEI Embedding | 8080 | BGE-M3 稠密向量服务（仅全栈）|
| TEI Reranker | 8081 | bge-reranker-v2-m3 精排服务（仅全栈）|

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
