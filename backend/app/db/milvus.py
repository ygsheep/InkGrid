"""Milvus client + collection schema + partition 管理。

设计参考：plan/后端设计方案.md §4.3
- 单 collection inkgrid_chunks
- partition 表达三级范围：global / channel_{slug}
- BGE-M3 稠密(1024) + 稀疏(SPARSE_FLOAT_VECTOR)
- 稠密索引 HNSW，稀疏索引 SPARSE_INVERTED_INDEX

pymilvus 2.4 的 MilvusClient 是同步客户端，用 asyncio.to_thread 包装为异步。
"""
import asyncio
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("db.milvus")

# ===== Collection Schema 常量 =====

COLLECTION_FIELDS = {
    "id": "VARCHAR(64) pk",
    "doc_id": "VARCHAR(64)",
    "channel": "VARCHAR(32)",
    "article_slug": "VARCHAR(64)",
    "heading": "VARCHAR(200)",
    "tags": "JSON",
    "content": "VARCHAR(8192)",
    "vector_dense": "FLOAT_VECTOR(1024)",
    "vector_sparse": "SPARSE_FLOAT_VECTOR",
}

DENSE_DIM = 1024  # BGE-M3 稠密维度
GLOBAL_PARTITION = "global"


class MilvusStore:
    """Milvus 向量库封装（同步 client + 异步包装）。"""

    def __init__(self) -> None:
        self._client: Any = None  # MilvusClient，懒加载

    def _get_client(self) -> Any:
        """获取同步 MilvusClient 单例。"""
        if self._client is None:
            from pymilvus import MilvusClient

            settings = get_settings()
            uri = f"http://{settings.milvus_host}:{settings.milvus_port}"
            self._client = MilvusClient(uri=uri)
            logger.info("milvus_client_created", uri=uri)
        return self._client

    async def init_collection(self) -> None:
        """初始化 collection + 索引 + global partition。

        幂等：已存在则跳过。应在应用启动时调用。
        """
        await asyncio.to_thread(self._init_collection_sync)

    def _init_collection_sync(self) -> None:
        from pymilvus import DataType, MilvusClient

        client = self._get_client()
        settings = get_settings()
        col_name = settings.milvus_collection

        if client.has_collection(col_name):
            logger.info("milvus_collection_exists", collection=col_name)
            return

        # 创建 schema
        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True)
        schema.add_field("vector_dense", DataType.FLOAT_VECTOR, dim=DENSE_DIM)
        schema.add_field("vector_sparse", DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field("doc_id", DataType.VARCHAR, max_length=64)
        schema.add_field("channel", DataType.VARCHAR, max_length=32)
        schema.add_field("article_slug", DataType.VARCHAR, max_length=64)
        schema.add_field("heading", DataType.VARCHAR, max_length=200)
        schema.add_field("tags", DataType.JSON)
        schema.add_field("content", DataType.VARCHAR, max_length=8192)

        # 索引
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector_dense",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        index_params.add_index(
            field_name="vector_sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
        )

        client.create_collection(
            collection_name=col_name,
            schema=schema,
            index_params=index_params,
        )

        # 创建 global partition
        if settings.milvus_use_partition:
            client.create_partition(col_name, GLOBAL_PARTITION)

        logger.info("milvus_collection_created", collection=col_name)

    async def ensure_partition(self, partition_name: str) -> None:
        """确保 partition 存在（如不存在则创建）。"""
        await asyncio.to_thread(self._ensure_partition_sync, partition_name)

    def _ensure_partition_sync(self, partition_name: str) -> None:
        client = self._get_client()
        settings = get_settings()
        col_name = settings.milvus_collection

        try:
            client.create_partition(col_name, partition_name)
            logger.info("milvus_partition_created", partition=partition_name)
        except Exception as e:
            # 已存在不算错误
            if "already exists" not in str(e).lower():
                raise

    async def insert_chunks(self, partition: str, chunks: list[dict]) -> None:
        """批量写入 chunks 到指定 partition。

        每个 chunk dict 需含: id, doc_id, channel, article_slug, heading,
        tags(list), content, vector_dense(list[float]), vector_sparse(dict[int,float])
        """
        if not chunks:
            return
        await asyncio.to_thread(self._insert_chunks_sync, partition, chunks)

    def _insert_chunks_sync(self, partition: str, chunks: list[dict]) -> None:
        client = self._get_client()
        settings = get_settings()
        col_name = settings.milvus_collection

        # 确保分区存在
        self._ensure_partition_sync(partition)

        client.insert(
            collection_name=col_name,
            data=chunks,
            partition_name=partition,
        )
        # flush 让 growing segment 转 sealed segment 并建索引，
        # 确保写入后立即可被 search 检索到（文章发布是低频操作，flush 开销可接受）
        client.flush(col_name)
        logger.info(
            "milvus_chunks_inserted",
            partition=partition,
            count=len(chunks),
        )

    async def delete_by_doc(self, doc_id: str) -> None:
        """按 doc_id 删除所有相关向量。"""
        await asyncio.to_thread(self._delete_by_doc_sync, doc_id)

    def _delete_by_doc_sync(self, doc_id: str) -> None:
        client = self._get_client()
        settings = get_settings()
        col_name = settings.milvus_collection

        client.delete(
            collection_name=col_name,
            filter=f'doc_id == "{doc_id}"',
        )
        logger.info("milvus_chunks_deleted", doc_id=doc_id)

    async def search_dense(
        self,
        query_dense: list[float],
        partition_names: list[str] | None = None,
        filter_expr: str = "",
        top_k: int = 20,
    ) -> list[dict]:
        """稠密向量检索，返回 top_k 结果。

        返回: [{id, doc_id, channel, article_slug, heading, tags, content, score}]
        score = 1 - distance（COSINE 距离转相似度）
        """
        return await asyncio.to_thread(
            self._search_dense_sync,
            query_dense,
            partition_names,
            filter_expr,
            top_k,
        )

    def _search_dense_sync(
        self,
        query_dense: list[float],
        partition_names: list[str] | None,
        filter_expr: str,
        top_k: int,
    ) -> list[dict]:
        client = self._get_client()
        settings = get_settings()
        col_name = settings.milvus_collection

        output_fields = [
            "id", "doc_id", "channel", "article_slug",
            "heading", "tags", "content",
        ]

        results = client.search(
            collection_name=col_name,
            data=[query_dense],
            anns_field="vector_dense",
            limit=top_k,
            partition_names=partition_names,
            filter=filter_expr or None,
            output_fields=output_fields,
        )

        return self._parse_search_results(results)

    async def search_sparse(
        self,
        query_sparse: dict[int, float],
        partition_names: list[str] | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        """稀疏向量检索（BM25 视角）。

        query_sparse 为空 dict 时返回空列表。
        """
        if not query_sparse:
            return []
        return await asyncio.to_thread(
            self._search_sparse_sync,
            query_sparse,
            partition_names,
            top_k,
        )

    def _search_sparse_sync(
        self,
        query_sparse: dict[int, float],
        partition_names: list[str] | None,
        top_k: int,
    ) -> list[dict]:
        client = self._get_client()
        settings = get_settings()
        col_name = settings.milvus_collection

        output_fields = [
            "id", "doc_id", "channel", "article_slug",
            "heading", "tags", "content",
        ]

        results = client.search(
            collection_name=col_name,
            data=[query_sparse],
            anns_field="vector_sparse",
            limit=top_k,
            partition_names=partition_names,
            output_fields=output_fields,
        )

        return self._parse_search_results(results)

    def _parse_search_results(self, results: Any) -> list[dict]:
        """解析 Milvus search 返回为标准 chunk dict 列表。"""
        chunks: list[dict] = []
        if not results:
            return chunks

        # MilvusClient.search 返回 [[{id, distance, entity: {...}}]]
        for hit in results[0]:
            entity = hit.get("entity", {}) if isinstance(hit, dict) else {}
            distance = hit.get("distance", 1.0) if isinstance(hit, dict) else 1.0
            # COSINE 距离越小越相似，转 score（0~1）
            score = max(0.0, 1.0 - distance)
            chunks.append({
                "id": entity.get("id", hit.get("id", "")),
                "doc_id": entity.get("doc_id", ""),
                "channel": entity.get("channel", ""),
                "article_slug": entity.get("article_slug", ""),
                "heading": entity.get("heading", ""),
                "tags": entity.get("tags", []),
                "content": entity.get("content", ""),
                "score": score,
            })
        return chunks


# 单例
milvus_store = MilvusStore()
