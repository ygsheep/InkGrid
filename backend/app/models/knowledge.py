"""知识库文档与分块模型（knowledge_docs / chunks 表）。

状态机：
- pending: 新建，分块进行中
- indexed: 解析 → 分块 → 写 PG → embedding → 写 Milvus 全部成功
- partial: PG chunks 成功但 Milvus 失败（不阻断，PG 有 chunks 缺向量）
- failed: 解析 / 分块失败
"""
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class KnowledgeDoc(Base, TimestampMixin):
    """知识库文档：一篇文章 / 一份上传文档 / 一条政策条目对应一条。

    - source_type: article | upload | policy
    - source_id: 关联源对象 ID（article 时为 posts.id）
    - chunk_count: 分块数量
    - status: pending | indexed | partial | failed
    - error_msg: 失败原因（前 400~500 字）
    """

    __tablename__ = "knowledge_docs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 上传源文件元数据（article 类型均为 NULL；upload 类型记录原始上传信息）
    original_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    source_format: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # md | txt | pdf | docx（article 为 NULL）
    mime_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # 浏览器上报的 MIME，下载时还原 Content-Type
    source_size: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  # 源文件字节数，用于看板容量统计与配额校验
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    channel_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 级联删除 chunks：删 doc 时一并删 chunks（pipeline 依赖此配置）
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="doc",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # 关联频道（admin 列表需展示频道信息，selectin 预加载避免 N+1）
    channel: Mapped["Channel | None"] = relationship(  # noqa: F821
        lazy="selectin",
    )


class Chunk(Base):
    """分块：与 Milvus 向量一一对应。

    - seq: 块序号（同 doc 内从 0 递增）
    - embedding_id: Milvus 主键，格式 f"{doc_id}_{seq}"，未写入 Milvus 时为 None
    - metadata_: Python 属性名带下划线，映射到 PG 列 metadata（保留字）
    """

    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    doc_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_docs.id", ondelete="CASCADE"),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # metadata 是 SQLAlchemy 保留字，必须用列别名
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    doc: Mapped["KnowledgeDoc"] = relationship(back_populates="chunks")
