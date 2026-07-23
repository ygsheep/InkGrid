"""MinIO 对象存储:图片上传与访问。

bucket 在 docker-compose.dev.yml 的 minio-init 中自动创建并设为公开读。
上传的图片通过 {public_base}/{bucket}/{object_name} 直接访问。
"""
import uuid
from datetime import datetime
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

settings = get_settings()


# 允许的图片 MIME 类型
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}

# 最大图片大小:10MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# 扩展名映射
EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def _get_client() -> Minio:
    """创建 MinIO 客户端(每次调用创建,因为 minio SDK 的 client 是轻量的)。"""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket(client: Minio) -> None:
    """确保 bucket 存在(不存在则创建并设为公开读)。"""
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
        # 设为公开读
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{settings.minio_bucket}/*"],
                }
            ],
        }
        import json

        client.set_bucket_policy(settings.minio_bucket, json.dumps(policy))


def upload_image(
    content: bytes,
    content_type: str,
    filename: str | None = None,
) -> str:
    """上传图片到 MinIO,返回可公开访问的 URL。

    Args:
        content: 图片二进制数据
        content_type: MIME 类型(如 image/png)
        filename: 原始文件名(仅用于扩展名推断,可选)

    Returns:
        图片的公开访问 URL

    Raises:
        ValueError: 如果类型不允许或大小超限
        S3Error: MinIO 操作失败
    """
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"不支持的图片类型: {content_type}")

    if len(content) > MAX_IMAGE_SIZE:
        raise ValueError(f"图片大小超过限制(最大 {MAX_IMAGE_SIZE // 1024 // 1024}MB)")

    # 生成 object 名:images/{年月}/{uuid}{ext}
    ext = EXT_BY_TYPE.get(content_type, "")
    if not ext and filename:
        import os

        ext = os.path.splitext(filename)[1] or ""
    now = datetime.utcnow()
    object_name = f"images/{now.strftime('%Y%m')}/{uuid.uuid4().hex}{ext}"

    client = _get_client()
    _ensure_bucket(client)

    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )

    # 构造公开访问 URL
    # dev: http://localhost:9000/inkgrid/images/202607/xxx.png
    # prod: 由 Nginx/CDN 代理,endpoint 通常是内部地址
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"
