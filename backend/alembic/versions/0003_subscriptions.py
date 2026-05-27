"""create subscriptions and subscription_results

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-23

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "fincode_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("fincode_customers.id"),
            nullable=False,
        ),
        sa.Column(
            "fincode_card_id",
            sa.BigInteger(),
            sa.ForeignKey("fincode_cards.id"),
            nullable=False,
        ),
        sa.Column("fincode_subscription_id", sa.String(128), nullable=True, unique=True),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("fincode_plan_id", sa.String(128), nullable=False),
        sa.Column("plan_name", sa.String(255), nullable=False),
        sa.Column("plan_amount", sa.Integer(), nullable=False),
        sa.Column("plan_interval", sa.String(32), nullable=False),
        sa.Column("plan_snapshot", JSONB(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])

    # partial unique index: one active subscription per user (race-safe)
    op.create_index(
        "uq_subscriptions_active_user",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "subscription_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "subscription_id",
            sa.BigInteger(),
            sa.ForeignKey("subscriptions.id"),
            nullable=False,
        ),
        sa.Column("fincode_subscription_id", sa.String(128), nullable=False),
        sa.Column("fincode_payment_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("charged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fincode_response", JSONB(), nullable=True),
        sa.UniqueConstraint(
            "fincode_subscription_id",
            "fincode_payment_id",
            name="uq_subscription_results_sub_payment",
        ),
    )
    op.create_index(
        "ix_subscription_results_subscription_id",
        "subscription_results",
        ["subscription_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_subscription_results_subscription_id", table_name="subscription_results")
    op.drop_table("subscription_results")
    op.drop_index("uq_subscriptions_active_user", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
