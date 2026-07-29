"""Add knowledge_documents table (Phase 2)

Revision ID: 002_knowledge
Revises: 001_initial
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_knowledge"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "visibility",
            sa.Enum("private", "member", name="knowledge_visibility_enum"),
            nullable=False,
            server_default="private",
        ),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_documents_user_visibility", "knowledge_documents", ["user_id", "visibility"])
    op.create_index("ix_knowledge_documents_visibility", "knowledge_documents", ["visibility"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_visibility", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_user_visibility", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
