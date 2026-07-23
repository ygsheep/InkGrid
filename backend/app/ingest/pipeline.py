"""入库编排：parse → chunk → write PG → embedding → write Milvus。

状态机：pending → indexed（PG chunks + Milvus 向量均成功）| failed（解析/分块失败）| partial（PG chunks 成功但 Milvus 失败）。
Milvus 写入失败不阻断入库（PG 已有 chunks，仅缺向量），记录 warning，
符合设计原则"RAG 失败不能让博客宕机"。
"""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.db.milvus import milvus_store
from app.ingest.chunker import chunk_document
from app.ingest.milvus_writer import write_chunks_to_milvus
from app.ingest.parser import parse_markdown
from app.models.knowledge import Chunk, KnowledgeDoc
from app.models.post import Post

logger = get_logger("ingest.pipeline")


async def ingest_article(db: AsyncSession, post_id: UUID) -> KnowledgeDoc:
    """文章入库管道：解析 → 分块 → 写 PG → embedding → 写 Milvus。

    流程：
    1. 加载文章（含 channel）
    2. 删旧 KnowledgeDoc（如果存在）+ 旧 chunks（级联）+ 旧 Milvus 向量
    3. 创建新 KnowledgeDoc（status=pending）
    4. 解析 + 分块
    5. 批量插入 chunks，更新 doc.chunk_count
    6. embedding + 写 Milvus + 回填 chunk.embedding_id
       - 成功 → status=indexed
       - 失败 → status=partial（PG 有 chunks，缺向量），不阻断
    7. 解析/分块失败 → status=failed + error_msg

    返回最终 KnowledgeDoc。
    """
    # 1. 加载文章（joinedload channel 拿 slug，用于 milvus partition 路由）
    stmt = select(Post).options(joinedload(Post.channel)).where(Post.id == post_id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError(f"post {post_id} not found")

    # 2. 删旧 doc + chunks（按 source_id 找旧 doc）+ 旧 Milvus 向量
    old_docs_stmt = select(KnowledgeDoc).where(
        KnowledgeDoc.source_type == "article",
        KnowledgeDoc.source_id == post_id,
    )
    old_docs = (await db.execute(old_docs_stmt)).scalars().all()
    for old_doc in old_docs:
        # 删旧 Milvus 向量（失败不阻断，避免 Milvus 不可用时无法重建）
        try:
            await milvus_store.delete_by_doc(str(old_doc.id))
        except Exception as e:
            logger.warning(
                "milvus_delete_failed",
                doc_id=str(old_doc.id),
                error=str(e),
            )
        # 级联删除 chunks（关系已配置 cascade=all,delete-orphan）
        await db.delete(old_doc)
    await db.flush()

    # 3. 创建新 doc
    doc = KnowledgeDoc(
        source_type="article",
        source_id=post.id,
        title=post.title,
        channel_id=post.channel_id,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    try:
        # 4. 解析 + 分块
        parsed = parse_markdown(
            title=post.title,
            content_md=post.content_md,
            slug=post.slug,
        )
        chunk_results = chunk_document(parsed, tags=post.tags)

        # 5. 批量插入 chunks（保留引用以回填 embedding_id）
        chunk_objs: list[Chunk] = []
        for cr in chunk_results:
            chunk = Chunk(
                doc_id=doc.id,
                seq=cr.seq,
                content=cr.content,
                token_count=cr.token_count,
                metadata_=cr.metadata,
            )
            db.add(chunk)
            chunk_objs.append(chunk)

        doc.parsed_text = parsed.text
        doc.chunk_count = len(chunk_results)

        # 6. embedding + 写 Milvus + 回填 embedding_id
        # 成功 → indexed；失败 → partial（PG 有 chunks，缺向量），不阻断入库
        try:
            channel_slug = post.channel.slug if post.channel else ""
            embedding_ids = await write_chunks_to_milvus(
                doc_id=str(doc.id),
                chunks=chunk_objs,
                channel_slug=channel_slug,
                article_slug=post.slug,
                tags=post.tags or [],
            )
            for chunk, eid in zip(chunk_objs, embedding_ids):
                chunk.embedding_id = eid
            doc.status = "indexed"
            doc.error_msg = None
            logger.info(
                "article_vectorized",
                post_id=str(post_id),
                doc_id=str(doc.id),
                vectors=len(embedding_ids),
            )
        except Exception as e:
            doc.status = "partial"
            doc.error_msg = f"milvus_write_failed: {str(e)[:400]}"
            logger.warning(
                "article_vectorize_failed",
                post_id=str(post_id),
                doc_id=str(doc.id),
                error=str(e),
            )

        logger.info(
            "article_indexed",
            post_id=str(post_id),
            doc_id=str(doc.id),
            chunks=doc.chunk_count,
            status=doc.status,
        )
    except Exception as e:
        doc.status = "failed"
        doc.error_msg = str(e)[:500]
        logger.exception("article_index_failed", post_id=str(post_id), error=str(e))
        raise

    await db.flush()
    return doc


async def remove_article_chunks(db: AsyncSession, post_id: UUID) -> int:
    """删除文章对应的 KnowledgeDoc + chunks + Milvus 向量（下架/删除时调用）。

    返回删除的 doc 数量。
    """
    stmt = select(KnowledgeDoc).where(
        KnowledgeDoc.source_type == "article",
        KnowledgeDoc.source_id == post_id,
    )
    docs = (await db.execute(stmt)).scalars().all()
    count = 0
    for doc in docs:
        # 删 Milvus 向量（失败不阻断 PG 清理）
        try:
            await milvus_store.delete_by_doc(str(doc.id))
        except Exception as e:
            logger.warning(
                "milvus_delete_failed",
                doc_id=str(doc.id),
                error=str(e),
            )
        # 删 chunks
        await db.execute(delete(Chunk).where(Chunk.doc_id == doc.id))
        await db.delete(doc)
        count += 1
    await db.flush()
    logger.info("article_chunks_removed", post_id=str(post_id), removed=count)
    return count
