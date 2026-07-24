"""Q&A 写入 Milvus：审核通过后把 Q&A 对写入向量库。

与 article chunk 共享同一个 collection，用 chunk_type=qa 区分。
content 字段存问题文本（用于 embedding 检索），answer 字段存答案。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.db.milvus import CHUNK_TYPE_QA, GLOBAL_PARTITION, milvus_store
from app.ingest.embedder import embedder
from app.models.post import Post
from app.models.qa_pair import QaPair

logger = get_logger("qa.milvus_writer")


async def write_qa_to_milvus(db: AsyncSession, qa: QaPair) -> str:
    """把单个 Q&A 对写入 Milvus。

    Returns:
        Milvus chunk_id（用于回填 qa.milvus_chunk_id）
    """
    # 加载文章信息（用于 article_slug, channel）
    post = await db.get(Post, qa.article_id)
    article_slug = post.slug if post else ""
    channel_slug = ""
    if post and post.channel_id:
        from app.models.channel import Channel
        channel = await db.get(Channel, post.channel_id)
        channel_slug = channel.slug if channel else ""

    # embedding 问题文本
    dense_vecs, sparse_vecs = await embedder.embed_batch([qa.question])
    dense = dense_vecs[0]
    sparse = sparse_vecs[0]

    # 组装数据
    chunk_id = f"qa_{qa.id}"
    data = [{
        "id": chunk_id,
        "doc_id": str(qa.article_id),
        "channel": channel_slug,
        "article_slug": article_slug,
        "heading": "",
        "tags": [],
        "content": qa.question,
        "chunk_type": CHUNK_TYPE_QA,
        "answer": qa.answer,
        "vector_dense": dense,
        "vector_sparse": sparse,
    }]

    partition = f"channel_{channel_slug}" if channel_slug else GLOBAL_PARTITION
    await milvus_store.insert_chunks(partition, data)

    logger.info(
        "qa_milvus_written",
        qa_id=str(qa.id),
        chunk_id=chunk_id,
        article_slug=article_slug,
    )
    return chunk_id


async def delete_qa_from_milvus(qa: QaPair) -> None:
    """从 Milvus 删除 Q&A 向量。"""
    if not qa.milvus_chunk_id:
        return
    try:
        settings = get_settings()
        client = milvus_store._get_client()
        client.delete(
            collection_name=settings.milvus_collection,
            filter=f'id == "{qa.milvus_chunk_id}"',
        )
        logger.info("qa_milvus_deleted", chunk_id=qa.milvus_chunk_id)
    except Exception as e:
        logger.warning("qa_milvus_delete_failed", chunk_id=qa.milvus_chunk_id, error=str(e))
