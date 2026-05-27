"""create fincode_customers and fincode_cards tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-23

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fincode_customers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("fincode_customer_id", sa.String(128), nullable=False, unique=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "fincode_cards",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "fincode_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("fincode_customers.id"),
            nullable=False,
        ),
        sa.Column("fincode_card_id", sa.String(128), nullable=False, unique=True),
        sa.Column("brand", sa.String(32), nullable=False),
        sa.Column("last4", sa.String(4), nullable=False),
        sa.Column("exp_month", sa.Integer(), nullable=False),
        sa.Column("exp_year", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fincode_cards_user_id", "fincode_cards", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_fincode_cards_user_id", table_name="fincode_cards")
    op.drop_table("fincode_cards")
    op.drop_table("fincode_customers")
