"""add fulltext search index on articles

Revision ID: 0001_initial
Revises: None
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001_fulltext_search"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 在 articles 表的 title 和 summary 列上创建 GIN 全文搜索索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_articles_fulltext
        ON articles
        USING GIN (
            to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, ''))
        );
    """)
    # 中文全文搜索索引（使用 simple 配置，对中文分词友好）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_articles_fulltext_simple
        ON articles
        USING GIN (
            to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, ''))
        );
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_articles_fulltext;")
    op.execute("DROP INDEX IF EXISTS ix_articles_fulltext_simple;")
