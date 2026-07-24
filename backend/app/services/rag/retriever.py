"""范围路由 + BGE-M3 稠密/稀疏混合检索 + FAQ-boosted。

设计参考：plan/后端设计方案.md §6.1
- global → 搜全 collection（所有 partition）
- channel:xxx → partition=[channel_xxx]
- article:xxx → filter: article_slug == xxx（跨所有 partition 搜）
- FAQ-boosted: 先搜 chunk_type=qa 的 Q&A，高分命中可短路
"""
from app.core.logging import get_logger
from app.db.milvus import CHUNK_TYPE_ARTICLE, CHUNK_TYPE_QA
from app.db.milvus import milvus_store
from app.ingest.embedder import embedder

logger = get_logger("rag.retriever")

# 默认检索参数
DEFAULT_TOP_K_DENSE = 20
DEFAULT_TOP_K_SPARSE = 20

# FAQ 短路阈值（rerank 分数高于此值时直接用 FAQ 答案）
FAQ_SHORT_CIRCUIT_THRESHOLD = 0.8


class Retriever:
    """范围路由 + 混合检索 + FAQ-boosted。"""

    async def retrieve(
        self,
        query: str,
        scope_type: str = "global",
        scope_ref: str = "",
        top_k: int = DEFAULT_TOP_K_DENSE,
    ) -> list[dict]:
        """范围路由 + 稠密/稀疏混合检索（全部 chunk 类型）。

        Args:
            query: 用户问题（已增强的 query）
            scope_type: global | channel | article
            scope_ref: channel slug 或 article slug
            top_k: 每路检索的 top_k

        Returns:
            合并去重后的 chunks 列表（未 rerank），每个含:
            id, doc_id, channel, article_slug, heading, tags, content,
            chunk_type, answer, score
        """
        # 1. query embedding
        query_dense, query_sparse = await embedder.embed_query(query)

        # 2. 范围路由 → partition_names + filter_expr
        partition_names, filter_expr = self._resolve_scope(scope_type, scope_ref)

        # 3. 稠密检索
        dense_results = await milvus_store.search_dense(
            query_dense=query_dense,
            partition_names=partition_names,
            filter_expr=filter_expr,
            top_k=top_k,
        )
        logger.debug(
            "dense_search_done",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            hits=len(dense_results),
        )

        # 4. 稀疏检索（BM25 视角）
        sparse_results = await milvus_store.search_sparse(
            query_sparse=query_sparse,
            partition_names=partition_names,
            top_k=DEFAULT_TOP_K_SPARSE,
        )
        logger.debug(
            "sparse_search_done",
            hits=len(sparse_results),
        )

        # 5. 合并去重（按 id 去重，保留最高 score）
        merged = self._merge_dedupe(dense_results, sparse_results)
        logger.info(
            "retrieve_done",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            dense=len(dense_results),
            sparse=len(sparse_results),
            merged=len(merged),
        )
        return merged

    async def retrieve_faq(
        self,
        query: str,
        scope_type: str = "global",
        scope_ref: str = "",
        top_k: int = 10,
    ) -> list[dict]:
        """只搜 Q&A 类型（chunk_type=qa）的 chunks。

        Returns:
            FAQ chunks 列表，每个含 answer 字段
        """
        query_dense, query_sparse = await embedder.embed_query(query)
        partition_names, filter_expr = self._resolve_scope(scope_type, scope_ref)

        # 叠加 chunk_type == "qa" 过滤
        faq_filter = 'chunk_type == "qa"'
        if filter_expr:
            filter_expr = f"({filter_expr}) and {faq_filter}"
        else:
            filter_expr = faq_filter

        dense_results = await milvus_store.search_dense(
            query_dense=query_dense,
            partition_names=partition_names,
            filter_expr=filter_expr,
            top_k=top_k,
        )
        logger.info(
            "faq_retrieve_done",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            hits=len(dense_results),
        )
        return dense_results

    async def retrieve_articles(
        self,
        query: str,
        scope_type: str = "global",
        scope_ref: str = "",
        top_k: int = DEFAULT_TOP_K_DENSE,
    ) -> list[dict]:
        """只搜文章片段类型（chunk_type=article_chunk）的 chunks。"""
        query_dense, query_sparse = await embedder.embed_query(query)
        partition_names, filter_expr = self._resolve_scope(scope_type, scope_ref)

        # 叠加 chunk_type == "article_chunk" 过滤
        art_filter = 'chunk_type == "article_chunk"'
        if filter_expr:
            filter_expr = f"({filter_expr}) and {art_filter}"
        else:
            filter_expr = art_filter

        dense_results = await milvus_store.search_dense(
            query_dense=query_dense,
            partition_names=partition_names,
            filter_expr=filter_expr,
            top_k=top_k,
        )

        sparse_results = await milvus_store.search_sparse(
            query_sparse=query_sparse,
            partition_names=partition_names,
            top_k=DEFAULT_TOP_K_SPARSE,
        )

        # 过滤掉非 article_chunk 的稀疏结果（sparse 搜索无法加 filter）
        sparse_results = [
            r for r in sparse_results
            if r.get("chunk_type", CHUNK_TYPE_ARTICLE) == CHUNK_TYPE_ARTICLE
        ]

        merged = self._merge_dedupe(dense_results, sparse_results)
        logger.info(
            "article_retrieve_done",
            query=query[:50],
            scope=f"{scope_type}:{scope_ref}",
            merged=len(merged),
        )
        return merged

    def _resolve_scope(
        self, scope_type: str, scope_ref: str
    ) -> tuple[list[str] | None, str]:
        """根据 scope_type + scope_ref 解析为 Milvus partition_names + filter_expr。

        Returns:
            (partition_names, filter_expr)
            - partition_names: None 表示搜全 collection
            - filter_expr: 空字符串表示无过滤
        """
        if scope_type == "channel" and scope_ref:
            partition = f"channel_{scope_ref}"
            return [partition], ""
        elif scope_type == "article" and scope_ref:
            # article 范围用 filter，跨所有 partition 搜
            return None, f'article_slug == "{scope_ref}"'
        else:
            # global 或未指定 → 搜全 collection（所有 partition）
            return None, ""

    @staticmethod
    def _merge_dedupe(
        dense: list[dict], sparse: list[dict]
    ) -> list[dict]:
        """合并稠密+稀疏结果，按 id 去重，保留最高 score。"""
        seen: dict[str, dict] = {}
        for chunk in dense + sparse:
            cid = chunk.get("id", "")
            if cid not in seen or chunk["score"] > seen[cid]["score"]:
                seen[cid] = chunk
        # 按 score 降序
        return sorted(seen.values(), key=lambda c: c["score"], reverse=True)


# 单例
retriever = Retriever()
