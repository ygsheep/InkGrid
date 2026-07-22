# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 系统依赖（PostgreSQL client、构建工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 layer 缓存）
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# 拷贝源码
COPY . .

EXPOSE 8000

# 默认启动 web 进程；worker / beat 通过 compose 覆盖 command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
