"""KnowledgeDoc / Chunk 知识库文档与分块。

- KnowledgeDoc：一篇文章/上传文档/政策条目对应一条记录
- Chunk：分块，与 Milvus 向量一一对应（P0 阶段只写 PG，不写向量）
"""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class KnowledgeDoc(Base, UUIDPkMixin, TimestampMixin):
    """知识库文档：入库管道的元数据与状态。"""

    __tablename__ = "knowledge_docs"
    __table_args__ = (
        Index("ix_knowledge_docs_channel_status", "channel_id", "status"),
    )

    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # article|upload|policy
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # posts.id
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_uri: Mapped[str | None] = mapped_column(Text)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending|indexed|partial|failed
    error_msg: Mapped[str | None] = mapped_column(Text)

    chunks = relationship("Chunk", back_populates="doc", cascade="all, delete-orphan")


class Chunk(Base, UUIDPkMixin):
    """分块：与 Milvus 向量一一对应。"""

    __tablename__ = "chunks"
    __table_args__ = (Index("ix_chunks_doc_seq", "doc_id", "seq"),)

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_docs.id", ondelete="CASCADE"),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding_id: Mapped[str | None] = mapped_column(String(64))  # Milvus 主键
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    doc = relationship("KnowledgeDoc", back_populates="chunks")
