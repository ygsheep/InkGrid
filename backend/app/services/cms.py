"""文章发布编排：发布事件分发 + Next.js revalidate 通知。

后端在文章 CRUD 后调用 notify_revalidate，POST 到前端 /api/revalidate，
由前端调用 revalidateTag / revalidatePath 让 Next.js 重新生成受影响页面。

dev 模式下 fetch 的 next.revalidate / tags 也会缓存，
on-demand revalidate 是唯一能"发布即生效"的方式。
"""
import httpx

from app.config import get_settings

settings = get_settings()


async def notify_revalidate(
    *,
    paths: list[str] | None = None,
    tags: list[str] | None = None,
) -> None:
    """通知 Next.js 重新生成指定路径 / tag。

    失败不抛错（仅记录日志），避免阻塞主流程。

    paths: 如 ["/", "/posts", "/posts/slug-x"]
    tags:  如 ["posts", "post:slug-x"]
    """
    if not settings.next_revalidate_token:
        return  # 未配置 secret，跳过

    base = settings.next_public_api_base.rstrip("/")
    url = f"{base}/api/revalidate"
    payload = {
        "secret": settings.next_revalidate_token,
        "paths": paths or [],
        "tags": tags or [],
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code != 200:
                from app.core.logging import get_logger

                get_logger("cms").warning(
                    "revalidate_non_200",
                    status=r.status_code,
                    body=r.text[:200],
                )
    except Exception as e:
        from app.core.logging import get_logger

        get_logger("cms").warning("revalidate_failed", error=str(e))


def _tags_for_post(slug: str | None) -> list[str]:
    """文章相关 tag 列表。"""
    tags = ["posts"]
    if slug:
        tags.append(f"post:{slug}")
    return tags


def _paths_for_post(slug: str | None) -> list[str]:
    """文章相关路径列表。"""
    paths = ["/", "/posts"]
    if slug:
        paths.append(f"/posts/{slug}")
    return paths
