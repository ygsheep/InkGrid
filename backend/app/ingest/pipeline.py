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
from app.ingest.parser import ParsedDoc, parse_document, parse_markdown
from app.models.channel import Channel
from app.models.knowledge import Chunk, KnowledgeDoc
from app.models.post import Post
from app.services import storage
from app.services.upload_security import ValidatedDocument

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


# ===== 上传文档入库（source_type=upload） =====
# 与 ingest_article 共用状态机，但 source_id=None、不依赖 posts 表。
# 多格式上传：源文件归档 MinIO（raw_uri=对象键），按 source_format 分派解析器。


async def ingest_upload(
    db: AsyncSession,
    *,
    title: str,
    channel_id: UUID,
    validated: ValidatedDocument,
) -> KnowledgeDoc:
    """上传文档入库管道（source_type=upload，支持 md/txt/pdf/docx）。

    流程：
    1. 归档源文件到 MinIO → raw_uri（对象键），存元数据
    2. 按 source_format 分派解析器（md/txt 用已解码 text，pdf/docx 用 raw）
    3. 分块 → 写 PG chunks → embedding → 写 Milvus
    4. 状态机：indexed / partial（Milvus 失败）/ failed（解析失败）

    MinIO 归档失败视为硬失败（无法下载/重解析），向上抛出由调用方处理。
    解析失败标记 failed；Milvus 写入失败标记 partial（PG 有 chunks 缺向量）。
    """
    ch = await db.get(Channel, channel_id)
    if not ch:
        raise ValueError(f"channel {channel_id} not found")

    # 1. 归档源文件到 MinIO（硬失败：无法归档则上传失败）
    raw_uri = storage.upload_document(
        content=validated.raw,
        content_type=validated.content_type,
        filename=validated.filename,
    )

    doc = KnowledgeDoc(
        source_type="upload",
        source_id=None,
        title=title,
        raw_uri=raw_uri,
        original_filename=validated.filename,
        source_format=validated.source_format,
        mime_type=validated.content_type,
        source_size=validated.size,
        channel_id=channel_id,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    try:
        # 2. 按 source_format 分派解析器
        parsed = parse_document(
            title=title,
            source_format=validated.source_format,
            text=validated.text,
            raw=validated.raw,
            slug=None,
        )
        chunk_results = chunk_document(parsed, tags=None)

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

        try:
            embedding_ids = await write_chunks_to_milvus(
                doc_id=str(doc.id),
                chunks=chunk_objs,
                channel_slug=ch.slug,
                article_slug="",  # 上传文档没有 slug
                tags=[],
            )
            for chunk, eid in zip(chunk_objs, embedding_ids):
                chunk.embedding_id = eid
            doc.status = "indexed"
            doc.error_msg = None
            logger.info(
                "upload_vectorized",
                doc_id=str(doc.id),
                vectors=len(embedding_ids),
            )
        except Exception as e:
            doc.status = "partial"
            doc.error_msg = f"milvus_write_failed: {str(e)[:400]}"
            logger.warning(
                "upload_vectorize_failed",
                doc_id=str(doc.id),
                error=str(e),
            )

        logger.info(
            "upload_indexed",
            doc_id=str(doc.id),
            chunks=doc.chunk_count,
            status=doc.status,
            source_format=validated.source_format,
        )
    except Exception as e:
        # 解析/分块失败：标记 failed 但不抛异常，返回 doc 供批量上传逐文件收集结果
        # （硬失败如 channel 不存在、MinIO 归档失败已在上方抛出）
        doc.status = "failed"
        doc.error_msg = str(e)[:500]
        logger.exception("upload_index_failed", doc_id=str(doc.id), error=str(e))

    await db.flush()
    return doc


async def reindex_upload(db: AsyncSession, doc: KnowledgeDoc) -> KnowledgeDoc:
    """重新对已存在的 upload 文档做分块 + 写 Milvus。

    admin 触发的 reindex：
    - 删旧 chunks + 旧 Milvus 向量
    - 若有 parsed_text → 直接重新分块
    - 若 parsed_text 为空但 raw_uri 存在 → 从 MinIO 拉源文件重新解析（修复失败的 PDF/DOCX）
    - 重新 embedding + 写 Milvus，更新 status / chunk_count / error_msg

    若既无 parsed_text 也无 raw_uri，直接标记 failed。
    """
    # 删旧 Milvus 向量（失败不阻断）
    try:
        await milvus_store.delete_by_doc(str(doc.id))
    except Exception as e:
        logger.warning("milvus_delete_failed", doc_id=str(doc.id), error=str(e))

    # 删旧 chunks（保留 doc）
    await db.execute(delete(Chunk).where(Chunk.doc_id == doc.id))
    await db.flush()

    try:
        parsed = await _resolve_parsed_text(db, doc)
        chunk_results = chunk_document(parsed, tags=None)

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

        # 取 channel slug 用于 partition 路由
        ch = await db.get(Channel, doc.channel_id) if doc.channel_id else None
        channel_slug = ch.slug if ch else ""

        try:
            embedding_ids = await write_chunks_to_milvus(
                doc_id=str(doc.id),
                chunks=chunk_objs,
                channel_slug=channel_slug,
                article_slug="",
                tags=[],
            )
            for chunk, eid in zip(chunk_objs, embedding_ids):
                chunk.embedding_id = eid
            doc.status = "indexed"
            doc.error_msg = None
        except Exception as e:
            doc.status = "partial"
            doc.error_msg = f"milvus_write_failed: {str(e)[:400]}"
            logger.warning(
                "upload_reindex_vectorize_failed",
                doc_id=str(doc.id),
                error=str(e),
            )

        logger.info(
            "upload_reindexed",
            doc_id=str(doc.id),
            chunks=doc.chunk_count,
            status=doc.status,
        )
    except Exception as e:
        doc.status = "failed"
        doc.error_msg = str(e)[:500]
        logger.exception("upload_reindex_failed", doc_id=str(doc.id), error=str(e))
        raise

    await db.flush()
    return doc


async def _resolve_parsed_text(db: AsyncSession, doc: KnowledgeDoc) -> ParsedDoc:
    """获取 reindex 用的 ParsedDoc：优先用已有 parsed_text，否则从 MinIO 重新解析。

    - 有 parsed_text：直接构造 ParsedDoc（不重新解析标题，滑窗分块）
    - 无 parsed_text 但有 raw_uri：从 MinIO 拉源文件，按 source_format 重新解析
    - 两者皆无：抛 ValueError，由调用方标记 failed
    """
    if doc.parsed_text:
        return ParsedDoc(
            title=doc.title,
            text=doc.parsed_text,
            headings=[],
            slug=None,
        )
    if not doc.raw_uri:
        raise ValueError("no parsed_text and no raw_uri to reindex")

    # 从 MinIO 拉源文件重新解析（修复失败的 pdf/docx）
    resp = storage.get_object(doc.raw_uri)
    try:
        raw = resp.read()
    finally:
        resp.close()
        resp.release_conn()

    source_format = doc.source_format or "md"
    text: str | None = None
    if source_format in ("md", "txt"):
        # 文本类重新解码（md 强制 UTF-8，txt 兜底 chardet）
        from app.services.upload_security import _decode_text_content

        text = _decode_text_content(raw, source_format)
    parsed = parse_document(
        title=doc.title,
        source_format=source_format,
        text=text,
        raw=raw,
        slug=None,
    )
    return parsed


async def remove_upload_doc(db: AsyncSession, doc: KnowledgeDoc) -> None:
    """删除上传文档：Milvus 向量 + chunks + doc + MinIO 源文件。

    各步失败均不阻断主流程（Milvus/MinIO 清理失败仅记日志），
    但 PG 的 chunks + doc 删除是硬成功（保证前端列表立即消失）。
    """
    # 删 Milvus 向量（失败不阻断）
    try:
        await milvus_store.delete_by_doc(str(doc.id))
    except Exception as e:
        logger.warning("milvus_delete_failed", doc_id=str(doc.id), error=str(e))

    # 删 MinIO 源文件（失败不阻断，仅记日志）
    if doc.raw_uri:
        try:
            storage.delete_object(doc.raw_uri)
        except Exception as e:
            logger.warning(
                "minio_delete_failed",
                doc_id=str(doc.id),
                raw_uri=doc.raw_uri,
                error=str(e),
            )

    # 删 chunks + doc（级联删 chunks）
    await db.delete(doc)
    await db.flush()
    logger.info("upload_doc_removed", doc_id=str(doc.id), title=doc.title)
