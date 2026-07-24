"""knowledge base: posts 扩展为 notes + note_links/note_templates 表

将 posts 表扩展为通用笔记表（承载博客文章 + 私有知识库笔记）：
- 新增 category（7 层目录枚举）、folder_path（子目录树）、owner_id（笔者归属）
- 新增 is_moc（主题地图标记）、source_url（阅读笔记来源）
- channel_id 改为可空（未发布的私有笔记无频道）
- 现有文章数据回填 category='knowledge'（作为已发布知识）

新建表：
- note_links：笔记双链关系，支撑 [[双链]] 与反链面板
- note_templates：笔记模板，对应 05_Templates 目录

Revision ID: 0004_knowledge_base
Revises: 0003_qa_pairs
Create Date: 2026-07-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_knowledge_base"
down_revision = "0003_qa_pairs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. posts 表扩展列
    op.add_column(
        "posts",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column(
            "category",
            sa.String(20),
            nullable=False,
            server_default="knowledge",
        ),
    )
    op.add_column("posts", sa.Column("folder_path", sa.String(255), nullable=True))
    op.add_column(
        "posts",
        sa.Column(
            "is_moc",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("posts", sa.Column("source_url", sa.String(500), nullable=True))

    # 2. channel_id 改为可空（未发布的私有笔记无频道）
    op.alter_column(
        "posts",
        "channel_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # 3. 外键：owner_id -> admins.id
    op.create_foreign_key(
        "fk_posts_owner_id_admins",
        "posts",
        "admins",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. 新索引（知识库查询常用）
    op.create_index(
        "ix_posts_owner_category", "posts", ["owner_id", "category"]
    )
    op.create_index(
        "ix_posts_category_folder", "posts", ["category", "folder_path"]
    )

    # 5. note_links 表（双链）
    op.create_table(
        "note_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_title_raw", sa.String(200), nullable=False),
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
        sa.UniqueConstraint(
            "source_note_id",
            "target_title_raw",
            name="uq_note_links_source_target",
        ),
    )
    op.create_index("ix_note_links_source", "note_links", ["source_note_id"])
    op.create_index("ix_note_links_target", "note_links", ["target_note_id"])

    # 6. note_templates 表（模板）
    op.create_table(
        "note_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admins.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("description", sa.String(300), nullable=True),
        sa.Column("content_md", sa.Text, nullable=False),
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
        "ix_note_templates_owner_category",
        "note_templates",
        ["owner_id", "category"],
    )


def downgrade() -> None:
    # note_templates
    op.drop_index(
        "ix_note_templates_owner_category", table_name="note_templates"
    )
    op.drop_table("note_templates")

    # note_links
    op.drop_index("ix_note_links_target", table_name="note_links")
    op.drop_index("ix_note_links_source", table_name="note_links")
    op.drop_table("note_links")

    # posts 扩展列回滚
    op.drop_index("ix_posts_category_folder", table_name="posts")
    op.drop_index("ix_posts_owner_category", table_name="posts")
    op.drop_constraint(
        "fk_posts_owner_id_admins", "posts", type_="foreignkey"
    )
    op.alter_column(
        "posts",
        "channel_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("posts", "source_url")
    op.drop_column("posts", "is_moc")
    op.drop_column("posts", "folder_path")
    op.drop_column("posts", "category")
    op.drop_column("posts", "owner_id")
