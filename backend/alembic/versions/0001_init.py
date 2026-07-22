"""init schema

创建所有 P0 阶段表：admins / audit_logs / personas / channels / posts /
chat_sessions / chat_messages / knowledge_docs / chunks / site_settings。

Revision ID: 0001_init
Revises:
Create Date: 2026-07-22 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # admins
    op.create_table(
        "admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(100)),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target", sa.String(100)),
        sa.Column("meta", postgresql.JSONB),
    )

    # personas
    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("serial", sa.String(8), nullable=False, unique=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("tagline", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String)),
        sa.Column("avatar", sa.Text),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("scope", sa.String(20), nullable=False, server_default="global"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # channels
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("accent", sa.String(20)),
        sa.Column(
            "persona_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # posts
    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("excerpt", sa.String(500)),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("content_html", sa.Text),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("channels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String)),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("reading_time", sa.Integer),
        sa.Column("toc", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_posts_status_published_at", "posts", ["status", "published_at"])
    op.create_index("ix_posts_channel_published_at", "posts", ["channel_id", "published_at"])

    # chat_sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("anon_id", sa.String(64), index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "persona_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
        ),
        sa.Column("scope_type", sa.String(20), server_default="global"),
        sa.Column("scope_ref", sa.String(100)),
        sa.Column("title", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_sessions_anon_id", "chat_sessions", ["anon_id"])

    # chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", postgresql.JSONB),
        sa.Column("follow_ups", postgresql.ARRAY(sa.String)),
        sa.Column("tokens_in", sa.Integer),
        sa.Column("tokens_out", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_messages_session_created", "chat_messages", ["session_id", "created_at"])

    # knowledge_docs
    op.create_table(
        "knowledge_docs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True)),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("raw_uri", sa.Text),
        sa.Column("parsed_text", sa.Text),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("channels.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_msg", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_docs_channel_status", "knowledge_docs", ["channel_id", "status"])

    # chunks
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_docs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer),
        sa.Column("embedding_id", sa.String(64)),
        sa.Column("metadata", postgresql.JSONB),
    )
    op.create_index("ix_chunks_doc_seq", "chunks", ["doc_id", "seq"])

    # site_settings
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_name", sa.String(100), nullable=False),
        sa.Column("author", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("extra", postgresql.JSONB),
    )


def downgrade() -> None:
    op.drop_table("site_settings")
    op.drop_index("ix_chunks_doc_seq", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_knowledge_docs_channel_status", table_name="knowledge_docs")
    op.drop_table("knowledge_docs")
    op.drop_index("ix_chat_messages_session_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_anon_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index("ix_posts_channel_published_at", table_name="posts")
    op.drop_index("ix_posts_status_published_at", table_name="posts")
    op.drop_table("posts")
    op.drop_table("channels")
    op.drop_table("personas")
    op.drop_table("audit_logs")
    op.drop_table("admins")
