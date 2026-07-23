"""Meilisearch client + posts 索引初始化。

设计参考：plan/后端设计方案.md §5.2
- 单索引 posts，仅索引 status=published 的文章
- 可搜索字段：title / excerpt / content / channel_name / tags
- 可过滤字段：channel_slug / tags
- 可排序字段：published_at
- Meilisearch 1.6+ 内置 CJK 分词，中文无需额外分词器

meilisearch-python SDK 是同步客户端，用 asyncio.to_thread 包装为异步。
"""
import asyncio
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("db.meili")

# 索引配置：可搜索 / 可过滤 / 可排序字段
SEARCHABLE_ATTRIBUTES = ["title", "excerpt", "content", "channel_name", "tags"]
FILTERABLE_ATTRIBUTES = ["channel_slug", "tags"]
SORTABLE_ATTRIBUTES = ["published_at"]


class MeiliStore:
    """Meilisearch 封装（同步 SDK + 异步包装）。"""

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        """获取同步 meilisearch.Client 单例。"""
        if self._client is None:
            import meilisearch

            settings = get_settings()
            url = f"http://{settings.meili_host}:{settings.meili_port}"
            key = settings.meili_key or None
            self._client = meilisearch.Client(url, api_key=key)
            logger.info("meili_client_created", url=url)
        return self._client

    async def init_index(self) -> None:
        """初始化 posts 索引（幂等）。应在应用启动时调用。"""
        await asyncio.to_thread(self._init_index_sync)

    def _init_index_sync(self) -> None:
        settings = get_settings()
        if not settings.meili_enabled:
            logger.info("meili_disabled_skip_init")
            return
        client = self._get_client()
        index_uid = settings.meili_posts_index

        # 创建索引（已存在则跳过）
        try:
            client.create_index(index_uid, {"primaryKey": "id"})
            logger.info("meili_index_created", index=index_uid)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise
            logger.info("meili_index_exists", index=index_uid)

        index = client.index(index_uid)
        # 配置可搜索 / 可过滤 / 可排序字段（幂等 update）
        index.update_searchable_attributes(SEARCHABLE_ATTRIBUTES)
        index.update_filterable_attributes(FILTERABLE_ATTRIBUTES)
        index.update_sortable_attributes(SORTABLE_ATTRIBUTES)
        logger.info("meili_index_configured", index=index_uid)

    async def upsert_documents(self, docs: list[dict]) -> None:
        """批量 upsert 文档。"""
        if not docs:
            return
        await asyncio.to_thread(self._upsert_documents_sync, docs)

    def _upsert_documents_sync(self, docs: list[dict]) -> None:
        client = self._get_client()
        settings = get_settings()
        index = client.index(settings.meili_posts_index)
        index.add_documents(docs)
        logger.info("meili_upserted", count=len(docs))

    async def delete_document(self, doc_id: str) -> None:
        """按主键删除单个文档。"""
        await asyncio.to_thread(self._delete_document_sync, doc_id)

    def _delete_document_sync(self, doc_id: str) -> None:
        client = self._get_client()
        settings = get_settings()
        index = client.index(settings.meili_posts_index)
        index.delete_document(doc_id)
        logger.info("meili_deleted", doc_id=doc_id)

    async def delete_all_documents(self) -> None:
        """清空索引所有文档（全量重建前用）。"""
        await asyncio.to_thread(self._delete_all_documents_sync)

    def _delete_all_documents_sync(self) -> None:
        client = self._get_client()
        settings = get_settings()
        index = client.index(settings.meili_posts_index)
        index.delete_all_documents()
        logger.info("meili_all_deleted")

    async def search(
        self,
        query: str,
        limit: int = 20,
        filter_expr: str | None = None,
        sort: list[str] | None = None,
    ) -> dict:
        """搜索，返回原始 Meilisearch 响应。"""
        return await asyncio.to_thread(
            self._search_sync, query, limit, filter_expr, sort
        )

    def _search_sync(
        self,
        query: str,
        limit: int,
        filter_expr: str | None,
        sort: list[str] | None,
    ) -> dict:
        client = self._get_client()
        settings = get_settings()
        index = client.index(settings.meili_posts_index)

        opt_params: dict[str, Any] = {
            "limit": limit,
            "attributesToHighlight": ["title", "excerpt", "content"],
            "highlightPreTag": "<mark>",
            "highlightPostTag": "</mark>",
            "attributesToRetrieve": [
                "id",
                "slug",
                "title",
                "excerpt",
                "channel_slug",
                "channel_name",
                "tags",
                "published_at",
                "reading_time",
            ],
        }
        if filter_expr:
            opt_params["filter"] = filter_expr
        if sort:
            opt_params["sort"] = sort

        return index.search(query, opt_params)


meili_store = MeiliStore()
