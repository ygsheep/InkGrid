"""BGE-M3 批量 embedding：稠密 + 稀疏向量。双模式（TEI / 进程内 FlagEmbedding）。"""
import asyncio
from typing import Any

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ingest.embedder")
settings = get_settings()


class Embedder:
    """BGE-M3 embedding 客户端，双模式：

    - 配了 ``embedding_tei_url`` → 调 TEI 服务（仅稠密向量，稀疏返回空 dict 占位）
    - 否则 → 进程内 FlagEmbedding BGEM3FlagModel（稠密 + 稀疏 lexical_weights）

    进程内模型懒加载，首次调用时初始化，避免启动慢。
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._lock = asyncio.Lock()

    async def _ensure_model(self) -> None:
        """懒加载进程内 BGE-M3 模型（同步阻塞调用包装到 executor）。"""
        if self._model is None:
            async with self._lock:
                if self._model is None:
                    def _load() -> Any:
                        from FlagEmbedding import BGEM3FlagModel

                        return BGEM3FlagModel(
                            settings.embedding_model,
                            device=settings.embedding_device,
                            cache_dir=settings.embedding_cache_dir,
                        )

                    loop = asyncio.get_running_loop()
                    self._model = await loop.run_in_executor(None, _load)
                    logger.info(
                        "bge_m3_loaded",
                        model=settings.embedding_model,
                        device=settings.embedding_device,
                    )

    async def embed_batch(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """批量 embedding，返回 (稠密向量列表, 稀疏向量列表)。

        - TEI 模式仅返回稠密向量，稀疏为空 dict 占位（TEI /embed 不产稀疏）
        - 进程内模式返回稠密 + 稀疏（lexical_weights）
        """
        if not texts:
            return [], []

        if settings.embedding_tei_url:
            return await self._embed_tei(texts)
        return await self._embed_local(texts)

    async def _embed_tei(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """TEI 服务模式：POST /embed，仅返回稠密向量。"""
        url = settings.embedding_tei_url.rstrip("/") + "/embed"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json={"inputs": texts})
            r.raise_for_status()
            dense: list[list[float]] = r.json()
        # TEI /embed 仅返回稠密向量。稀疏用占位 {0: 0.01}（避免 Milvus 写入空 sparse 报错）；
        # sparse 检索由 query 端控制——TEI 模式下 query_sparse 也为空，retriever 会跳过 sparse 搜索
        sparse = [{0: 0.01} for _ in dense]
        logger.info(
            "embed_tei_done",
            count=len(dense),
            dim=len(dense[0]) if dense else 0,
        )
        return dense, sparse

    async def _embed_local(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """进程内 FlagEmbedding 模式：返回稠密 + 稀疏。"""
        await self._ensure_model()

        def _encode() -> tuple[list[list[float]], list[dict[int, float]]]:
            output = self._model.encode(
                texts,
                batch_size=settings.embedding_batch_size,
                return_dense=True,
                return_sparse=True,
            )
            dense_raw = output["dense_vecs"]
            dense = dense_raw.tolist() if hasattr(dense_raw, "tolist") else list(dense_raw)
            sparse = [
                {int(k): float(v) for k, v in weights.items()}
                for weights in output["lexical_weights"]
            ]
            return dense, sparse

        loop = asyncio.get_running_loop()
        dense, sparse = await loop.run_in_executor(None, _encode)
        logger.info(
            "embed_local_done",
            count=len(dense),
            dim=len(dense[0]) if dense else 0,
        )
        return dense, sparse

    async def embed_query(self, query: str) -> tuple[list[float], dict[int, float]]:
        """单条 query embedding，返回 (稠密向量, 稀疏向量)。

        TEI 模式下稀疏返回空 dict（TEI /embed 不产稀疏向量），
        retriever.search_sparse 收到空 dict 会跳过 sparse 检索，避免用占位向量搜 Milvus。
        写入端的 sparse 占位由 embed_batch 处理（Milvus 写入要求非空 sparse）。
        """
        dense, sparse = await self.embed_batch([query])
        if settings.embedding_tei_url:
            # TEI 模式：query 端无需占位，返回空 dict 让 retriever 跳过 sparse 检索
            return dense[0], {}
        return dense[0], sparse[0]


embedder = Embedder()
