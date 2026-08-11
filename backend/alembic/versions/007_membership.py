"""Membership tables — orders, codes, redemptions."""
from alembic import op
import sqlalchemy as sa

revision = "007_membership"
down_revision = "006_media_vlm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "membership_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("external_order_id", sa.String(128), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="webhook"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_order_id"),
    )
    op.create_index("ix_membership_orders_user_id", "membership_orders", ["user_id"])

    op.create_table(
        "membership_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_membership_codes_code", "membership_codes", ["code"])

    op.create_table(
        "membership_redemptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["code_id"], ["membership_codes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_membership_redemptions_user_id", "membership_redemptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_membership_redemptions_user_id", table_name="membership_redemptions")
    op.drop_table("membership_redemptions")
    op.drop_index("ix_membership_codes_code", table_name="membership_codes")
    op.drop_table("membership_codes")
    op.drop_index("ix_membership_orders_user_id", table_name="membership_orders")
    op.drop_table("membership_orders")
