"""Add VLM fields to media_assets (Batch 5)

Revision ID: 006_media_vlm
Revises: 005_knowledge_facts
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_media_vlm"
down_revision: Union[str, None] = "005_knowledge_facts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_assets", sa.Column("thumbnail_uri", sa.String(length=1024), nullable=True))
    op.add_column("media_assets", sa.Column("vlm_caption", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("vlm_structured", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("vlm_quality", sa.Float(), nullable=True))
    op.add_column("media_assets", sa.Column("vlm_engine", sa.String(length=32), nullable=True))
    op.add_column("media_assets", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("media_assets", sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="ready"))
    op.create_index("ix_media_assets_content_hash", "media_assets", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_media_assets_content_hash", table_name="media_assets")
    op.drop_column("media_assets", "parse_status")
    op.drop_column("media_assets", "content_hash")
    op.drop_column("media_assets", "vlm_engine")
    op.drop_column("media_assets", "vlm_quality")
    op.drop_column("media_assets", "vlm_structured")
    op.drop_column("media_assets", "vlm_caption")
    op.drop_column("media_assets", "thumbnail_uri")
