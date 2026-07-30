"""Add knowledge_tables and knowledge_facts (Batch 4)

Revision ID: 005_knowledge_facts
Revises: 004_media_assets
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_knowledge_facts"
down_revision: Union[str, None] = "004_media_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_tables",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doc_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("caption", sa.String(length=512), nullable=True),
        sa.Column("cells_json", sa.Text(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=True),
        sa.Column("quality_json", sa.Text(), nullable=True),
        sa.Column("section_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_tables_doc_id", "knowledge_tables", ["doc_id"])
    op.create_index("ix_knowledge_tables_user_id", "knowledge_tables", ["user_id"])

    op.create_table(
        "knowledge_facts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.String(length=36), nullable=False),
        sa.Column("table_id", sa.String(length=36), nullable=True),
        sa.Column("company", sa.String(length=256), nullable=True),
        sa.Column("metric_code", sa.String(length=64), nullable=True),
        sa.Column("metric_name", sa.String(length=256), nullable=True),
        sa.Column("period", sa.String(length=32), nullable=True),
        sa.Column("value_num", sa.Numeric(precision=24, scale=4), nullable=True),
        sa.Column("value_text", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_facts_user_id", "knowledge_facts", ["user_id"])
    op.create_index("ix_knowledge_facts_doc_id", "knowledge_facts", ["doc_id"])
    op.create_index("ix_knowledge_facts_table_id", "knowledge_facts", ["table_id"])
    op.create_index(
        "ix_knowledge_facts_query",
        "knowledge_facts",
        ["user_id", "company", "metric_code", "period"],
    )

    op.add_column(
        "knowledge_documents",
        sa.Column("doc_class", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("table_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "table_count")
    op.drop_column("knowledge_documents", "doc_class")
    op.drop_index("ix_knowledge_facts_query", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_table_id", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_doc_id", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_user_id", table_name="knowledge_facts")
    op.drop_table("knowledge_facts")
    op.drop_index("ix_knowledge_tables_user_id", table_name="knowledge_tables")
    op.drop_index("ix_knowledge_tables_doc_id", table_name="knowledge_tables")
    op.drop_table("knowledge_tables")
