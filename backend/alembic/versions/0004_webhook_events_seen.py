"""create webhook_events_seen table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-23

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_events_seen",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("fincode_event_id", sa.String(128), nullable=False, unique=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dlq_reason", sa.String(255), nullable=True),
    )
    op.create_index("ix_webhook_events_seen_event_type", "webhook_events_seen", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_webhook_events_seen_event_type", table_name="webhook_events_seen")
    op.drop_table("webhook_events_seen")
