"""入库编排：parse → chunk → write PG。

P0 阶段不含 Embedding 与 Milvus 写入（P1 接入）。
状态机：pending → indexed（成功）| failed（失败）。
"""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingest.chunker import chunk_document
from app.ingest.parser import parse_markdown
from app.models.knowledge import Chunk, KnowledgeDoc
from app.models.post import Post

logger = get_logger("ingest.pipeline")


async def ingest_article(db: AsyncSession, post_id: UUID) -> KnowledgeDoc:
    """文章入库管道：解析 → 分块 → 写 PG chunks 表。

    流程：
    1. 加载文章（含 channel）
    2. 删旧 KnowledgeDoc（如果存在）+ 旧 chunks（级联）
    3. 创建新 KnowledgeDoc（status=pending）
    4. 解析 + 分块
    5. 批量插入 chunks，更新 doc.chunk_count / status=indexed
    6. 失败则 status=failed + error_msg

    返回最终 KnowledgeDoc。
    """
    # 1. 加载文章
    stmt = select(Post).where(Post.id == post_id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError(f"post {post_id} not found")

    # 2. 删旧 doc + chunks（按 source_id 找旧 doc）
    old_docs_stmt = select(KnowledgeDoc).where(
        KnowledgeDoc.source_type == "article",
        KnowledgeDoc.source_id == post_id,
    )
    old_docs = (await db.execute(old_docs_stmt)).scalars().all()
    for old_doc in old_docs:
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

        # 5. 批量插入 chunks
        for cr in chunk_results:
            chunk = Chunk(
                doc_id=doc.id,
                seq=cr.seq,
                content=cr.content,
                token_count=cr.token_count,
                metadata_=cr.metadata,
            )
            db.add(chunk)

        doc.parsed_text = parsed.text
        doc.chunk_count = len(chunk_results)
        doc.status = "indexed"
        doc.error_msg = None
        logger.info(
            "article_indexed",
            post_id=str(post_id),
            doc_id=str(doc.id),
            chunks=doc.chunk_count,
        )
    except Exception as e:
        doc.status = "failed"
        doc.error_msg = str(e)[:500]
        logger.exception("article_index_failed", post_id=str(post_id), error=str(e))
        raise

    await db.flush()
    return doc


async def remove_article_chunks(db: AsyncSession, post_id: UUID) -> int:
    """删除文章对应的 KnowledgeDoc + chunks（下架/删除时调用）。

    返回删除的 doc 数量。
    """
    stmt = select(KnowledgeDoc).where(
        KnowledgeDoc.source_type == "article",
        KnowledgeDoc.source_id == post_id,
    )
    docs = (await db.execute(stmt)).scalars().all()
    count = 0
    for doc in docs:
        # 删 chunks
        await db.execute(delete(Chunk).where(Chunk.doc_id == doc.id))
        await db.delete(doc)
        count += 1
    await db.flush()
    logger.info("article_chunks_removed", post_id=str(post_id), removed=count)
    return count
