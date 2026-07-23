"""post_views table

新增文章访问日志表，用于看板 monthlyViews 精确统计（替换原估算）。

Revision ID: 0002_post_views
Revises: 0001_init
Create Date: 2026-07-23 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_post_views"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_views",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_post_views_post_created",
        "post_views",
        ["post_id", "created_at"],
    )
    op.create_index(
        "ix_post_views_created",
        "post_views",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_post_views_created", table_name="post_views")
    op.drop_index("ix_post_views_post_created", table_name="post_views")
    op.drop_table("post_views")
