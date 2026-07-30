"""Add media_assets table and document source fields (Batch 3)

Revision ID: 004_media_assets
Revises: 003_knowledge_chunks
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_media_assets"
down_revision: Union[str, None] = "003_knowledge_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("doc_id", sa.String(length=36), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(length=128), nullable=False, server_default="application/octet-stream"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="upload"),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("image_class", sa.String(length=64), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_quality", sa.Float(), nullable=True),
        sa.Column("ocr_engine", sa.String(length=32), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("bbox", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["knowledge_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_user_id", "media_assets", ["user_id"])
    op.create_index("ix_media_assets_doc_id", "media_assets", ["doc_id"])

    op.add_column(
        "knowledge_documents",
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="text"),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("mime_type", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "mime_type")
    op.drop_column("knowledge_documents", "source_type")
    op.drop_index("ix_media_assets_doc_id", table_name="media_assets")
    op.drop_index("ix_media_assets_user_id", table_name="media_assets")
    op.drop_table("media_assets")
