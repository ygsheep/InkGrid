"""Celery 实例 + 配置（broker/backend = Redis）。

启动 worker：celery -A app.tasks.celery_app worker -l info
启动 beat：celery -A app.tasks.celery_app beat -l info
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "inkgrid",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ingest_tasks",
        "app.tasks.reindex_tasks",
    ],
)

# 任务默认配置
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,  # 任务执行完才确认，避免崩溃丢任务
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # 一次只取一个任务，避免长任务阻塞
    result_expires=3600,
)


@celery_app.task(name="health.ping")
def ping() -> str:
    """健康检查任务。"""
    return "pong"
