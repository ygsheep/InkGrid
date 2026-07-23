"""bge-reranker-v2-m3 精排：双模式（TEI / 进程内 sentence-transformers CrossEncoder）。"""
import asyncio
from typing import Any

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("rag.reranker")
settings = get_settings()


class Reranker:
    """bge-reranker-v2-m3 精排客户端，双模式：

    - 配了 ``reranker_tei_url`` → 调 TEI 服务（POST /rerank）
    - 否则 → 进程内 sentence-transformers CrossEncoder（predict 打分）

    进程内模型懒加载，首次调用时初始化，避免启动慢。
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._lock = asyncio.Lock()

    async def _ensure_model(self) -> None:
        """懒加载进程内 CrossEncoder（同步阻塞调用包装到 executor）。"""
        if self._model is None:
            async with self._lock:
                if self._model is None:
                    def _load() -> Any:
                        from sentence_transformers import CrossEncoder

                        return CrossEncoder(
                            settings.reranker_model,
                            device=settings.reranker_device,
                        )

                    loop = asyncio.get_running_loop()
                    self._model = await loop.run_in_executor(None, _load)
                    logger.info(
                        "reranker_loaded",
                        model=settings.reranker_model,
                        device=settings.reranker_device,
                    )

    async def rerank(
        self, query: str, chunks: list[dict], top_n: int = 5
    ) -> list[dict]:
        """对 chunks 按 query 相关性精排，返回 top_n 个（每个 chunk 加 score 字段）。

        - score 为 float，越大越相关
        - 返回的 chunk 是输入 chunk 的浅拷贝 + score 字段，不修改原 chunk
        - chunk 中应含 ``content`` 字段用于打分；缺失时按空串处理
        """
        if not chunks:
            return []

        texts = [c.get("content", "") for c in chunks]
        if settings.reranker_tei_url:
            scores = await self._rerank_tei(query, texts)
        else:
            scores = await self._rerank_local(query, texts)

        ranked = [
            {**chunk, "score": float(score)} for chunk, score in zip(chunks, scores)
        ]
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_n]

    async def _rerank_tei(self, query: str, texts: list[str]) -> list[float]:
        """TEI 服务模式：POST /rerank，返回每个 text 的 score（按原顺序）。"""
        url = settings.reranker_tei_url.rstrip("/") + "/rerank"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json={"query": query, "texts": texts})
            r.raise_for_status()
            results = r.json()  # [{"index": 0, "score": 0.95}, ...]
        # TEI 可能按 score 排序或截断，按 index 还原回原顺序，缺失项记 0.0
        scores = [0.0] * len(texts)
        for item in results:
            idx = item["index"]
            if 0 <= idx < len(scores):
                scores[idx] = float(item["score"])
        logger.info("rerank_tei_done", count=len(texts), returned=len(results))
        return scores

    async def _rerank_local(self, query: str, texts: list[str]) -> list[float]:
        """进程内 CrossEncoder 模式：predict (query, text) pairs。"""
        await self._ensure_model()

        def _predict() -> list[float]:
            pairs = [(query, t) for t in texts]
            raw = self._model.predict(pairs)
            return [float(s) for s in raw]

        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(None, _predict)
        logger.info("rerank_local_done", count=len(texts))
        return scores


reranker = Reranker()
