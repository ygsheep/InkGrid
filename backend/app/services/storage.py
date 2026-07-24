"""MinIO 对象存储:图片上传与访问 + 知识库源文件归档/下载。

bucket 在 docker-compose.dev.yml 的 minio-init 中自动创建并设为公开读。
上传的图片通过 {public_base}/{bucket}/{object_name} 直接访问。
知识库源文件（PDF/DOCX/TXT/MD）归档到 docs/ 前缀，不公开，通过后台下载接口取回。
"""
import os
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


# ===== 知识库源文件归档（不公开，通过后台下载接口取回） =====


def upload_document(
    content: bytes,
    content_type: str,
    filename: str | None = None,
) -> str:
    """归档知识库上传的源文件到 MinIO，返回对象键（raw_uri）。

    与 upload_image 区别：
    - 归档到 docs/ 前缀，不对外公开（仅后台下载接口可读）
    - 不校验 MIME 白名单（已由 upload_security 按扩展名校验）
    - 不返回公开 URL，返回 object_name 供后续下载/重解析

    Args:
        content: 文件二进制
        content_type: 浏览器上报的 MIME（透传，下载时还原 Content-Type）
        filename: 原始文件名（仅用于扩展名推断）

    Returns:
        object_name，如 docs/202607/abc123.pdf
    """
    ext = ""
    if filename:
        ext = os.path.splitext(filename)[1] or ""
    now = datetime.utcnow()
    object_name = f"docs/{now.strftime('%Y%m')}/{uuid.uuid4().hex}{ext}"

    client = _get_client()
    _ensure_bucket(client)

    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type or "application/octet-stream",
    )
    return object_name


def get_object(object_name: str):
    """从 MinIO 拉取对象，返回 urllib3 Response（可流式读取）。

    供下载接口 StreamingResponse 使用：
        resp = get_object(raw_uri)
        return StreamingResponse(resp.stream(...), media_type=resp.headers.get("Content-Type"))

    Raises:
        S3Error: 对象不存在或 MinIO 不可达
    """
    client = _get_client()
    return client.get_object(settings.minio_bucket, object_name)


def delete_object(object_name: str) -> None:
    """删除 MinIO 对象（知识库文档删除时清理源文件归档）。

    对象不存在（NoSuchKey）视为成功（幂等）；其他 S3 错误向上抛出，
    由调用方决定是否阻断主流程（文档删除时建议 catch 后仅记日志）。
    """
    client = _get_client()
    try:
        client.remove_object(settings.minio_bucket, object_name)
    except S3Error as e:
        # 对象不存在视为成功（幂等）
        if e.code != "NoSuchKey":
            raise

