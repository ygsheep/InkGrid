"""后台上传路由:POST /admin/uploads/image。

接收 multipart 图片,存到 MinIO,返回公开访问 URL。
供 Bytemd 编辑器的图片上传 / 粘贴 / 拖拽使用。
"""
from fastapi import APIRouter, File, UploadFile

from app.core.errors import AppError
from app.core.logging import get_logger
from app.deps import AdminId
from app.schemas.common import envelope
from app.services.storage import MAX_IMAGE_SIZE, upload_image

router = APIRouter(prefix="/uploads")
logger = get_logger("admin.uploads")


@router.post("/image")
async def upload_image_route(
    _: AdminId,
    file: UploadFile = File(..., description="图片文件"),
) -> dict:
    """上传图片到对象存储,返回 URL。

    限制:
    - 类型:jpeg/png/gif/webp/svg
    - 大小:10MB
    """
    content = await file.read()
    content_type = file.content_type or ""

    # 简单类型校验(minio upload_image 也会校验,这里提前报错更友好)
    if not content_type:
        raise AppError("无法识别文件类型", status_code=400, code=4000)

    try:
        url = upload_image(
            content=content,
            content_type=content_type,
            filename=file.filename,
        )
    except ValueError as e:
        raise AppError(str(e), status_code=400, code=4000) from e
    except Exception as e:
        logger.error("image_upload_failed", error=str(e), filename=file.filename)
        raise AppError(
            f"图片上传失败: {e}", status_code=500, code=5000
        ) from e

    logger.info(
        "image_uploaded",
        filename=file.filename,
        content_type=content_type,
        size=len(content),
    )
    return envelope({"url": url, "size": len(content), "max_size": MAX_IMAGE_SIZE})
