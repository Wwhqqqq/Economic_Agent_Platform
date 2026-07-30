"""Add knowledge_chunks, ingest_jobs, document parse fields (Batch 1)

Revision ID: 003_knowledge_chunks
Revises: 002_knowledge
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_knowledge_chunks"
down_revision: Union[str, None] = "002_knowledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "parse_status",
            sa.Enum(
                "pending",
                "parsing",
                "ready",
                "failed",
                "needs_review",
                name="knowledge_parse_status_enum",
            ),
            nullable=False,
            server_default="ready",
        ),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("parser_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("quality_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("ndm_uri", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doc_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(length=32), nullable=False, server_default="paragraph"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section_path", sa.String(length=512), nullable=True),
        sa.Column("page_range", sa.String(length=64), nullable=True),
        sa.Column("block_ids", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_doc_id", "knowledge_chunks", ["doc_id"])
    op.create_index("ix_knowledge_chunks_user_id", "knowledge_chunks", ["user_id"])
    op.create_index("ix_knowledge_chunks_content_hash", "knowledge_chunks", ["content_hash"])
    op.create_index("ix_knowledge_chunks_doc_seq", "knowledge_chunks", ["doc_id", "seq"])

    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doc_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False, server_default="text_ingest"),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "parsing",
                "ready",
                "failed",
                "needs_review",
                name="ingest_job_status_enum",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_jobs_doc_id", "ingest_jobs", ["doc_id"])
    op.create_index("ix_ingest_jobs_user_id", "ingest_jobs", ["user_id"])
    op.create_index("ix_ingest_jobs_status", "ingest_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingest_jobs_status", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_user_id", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_doc_id", table_name="ingest_jobs")
    op.drop_table("ingest_jobs")

    op.drop_index("ix_knowledge_chunks_doc_seq", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_content_hash", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_user_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_doc_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_column("knowledge_documents", "page_count")
    op.drop_column("knowledge_documents", "ndm_uri")
    op.drop_column("knowledge_documents", "quality_score")
    op.drop_column("knowledge_documents", "parser_version")
    op.drop_column("knowledge_documents", "parse_status")
