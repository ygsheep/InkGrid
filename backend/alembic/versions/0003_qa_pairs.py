"""qa_pairs table

预生成 Q&A 对，用于 FAQ 检索与 followups 推荐。

Revision ID: 0003_qa_pairs
Revises: 0002_post_views
Create Date: 2026-07-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_qa_pairs"
down_revision = "0002_post_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_pairs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("milvus_chunk_id", sa.String(64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_qa_pairs_article_status",
        "qa_pairs",
        ["article_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_qa_pairs_article_status", table_name="qa_pairs")
    op.drop_table("qa_pairs")
