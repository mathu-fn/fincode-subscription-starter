"""make subscriptions.fincode_customer_id / fincode_card_id nullable

フリープラン（0円・ローカル完結）はカードと顧客を持たないため、両カラムを
NULL 許容にする。

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-31

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "subscriptions",
        "fincode_customer_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.alter_column(
        "subscriptions",
        "fincode_card_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    # フリープラン契約（NULL を持つ行）が残っていると NOT NULL 復帰は失敗する。
    op.alter_column(
        "subscriptions",
        "fincode_card_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "subscriptions",
        "fincode_customer_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
