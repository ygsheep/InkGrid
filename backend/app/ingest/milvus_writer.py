"""写入 Milvus：按频道 partition 写入。

把 PG chunks 经 embedding 后写入 Milvus，返回与 chunks 一一对应的
embedding_id 列表（即 Milvus 主键），供回填 Chunk.embedding_id。
"""
from app.core.logging import get_logger
from app.db.milvus import CHUNK_TYPE_ARTICLE, GLOBAL_PARTITION, milvus_store
from app.ingest.embedder import embedder

logger = get_logger("ingest.milvus_writer")


async def write_chunks_to_milvus(
    doc_id: str,
    chunks: list,  # Chunk ORM 对象列表
    channel_slug: str,
    article_slug: str,
    tags: list[str],
) -> list[str]:
    """把 PG chunks embedding 后写入 Milvus。

    流程：
    1. 提取 chunk.content 列表
    2. batch embedding（稠密+稀疏）
    3. 组装 milvus 数据（每个 chunk 一个 dict）
       - id: f"{doc_id}_{chunk.seq}"（唯一主键）
       - doc_id, channel, article_slug, heading, tags, content
       - vector_dense, vector_sparse
    4. partition = f"channel_{channel_slug}" if channel_slug else "global"
    5. milvus_store.insert_chunks(partition, data)
    6. 返回 embedding_id 列表（与 chunks 一一对应）
    """
    if not chunks:
        return []

    # 1. 提取文本
    texts = [c.content for c in chunks]

    # 2. batch embedding（稠密 + 稀疏）
    dense_vecs, sparse_vecs = await embedder.embed_batch(texts)

    # 3. 组装 milvus 数据
    partition = f"channel_{channel_slug}" if channel_slug else GLOBAL_PARTITION
    data: list[dict] = []
    embedding_ids: list[str] = []
    for chunk, dense, sparse in zip(chunks, dense_vecs, sparse_vecs):
        embedding_id = f"{doc_id}_{chunk.seq}"
        embedding_ids.append(embedding_id)
        meta = chunk.metadata_ or {}
        heading = meta.get("heading") or ""
        data.append({
            "id": embedding_id,
            "doc_id": doc_id,
            "channel": channel_slug or "",
            "article_slug": article_slug or "",
            "heading": heading,
            "tags": tags or [],
            "content": chunk.content,
            "chunk_type": CHUNK_TYPE_ARTICLE,
            "answer": "",
            "vector_dense": dense,
            "vector_sparse": sparse,
        })

    # 5. 写入 Milvus（ensure_partition 由 insert_chunks 内部处理）
    await milvus_store.insert_chunks(partition, data)
    logger.info(
        "milvus_write_done",
        doc_id=doc_id,
        partition=partition,
        count=len(data),
    )
    return embedding_ids
