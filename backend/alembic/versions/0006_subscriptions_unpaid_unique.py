"""extend uq_subscriptions_active_user to cover unpaid subscriptions

未払い（unpaid）契約は fincode 側のサブスクが生きたままなので、「1 ユーザー最大
1 契約」の partial unique index の対象に含めないと、unpaid 中に新規 active 契約が
作れてしまい二重課金になる。index の述語を ``status IN ('active', 'unpaid')`` に
張り替える。

張り替え前にデータ修復を行う: 旧 index は active のみを一意化していたため、同一
ユーザーに active と unpaid（または unpaid 同士）が並存し得る。active 優先・
created_at 降順で 1 件だけ残し、残り（常に unpaid 行）を cancelled に確定させる。
この修復は運用系の整合化であり業務操作ではないため audit_logs には記録しない。

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-03

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id, row_number() OVER (
                PARTITION BY user_id
                ORDER BY (status = 'active') DESC, created_at DESC, id DESC
            ) AS rn
            FROM subscriptions
            WHERE status IN ('active', 'unpaid')
        )
        UPDATE subscriptions s
        SET status = 'cancelled',
            cancelled_at = COALESCE(s.cancelled_at, now())
        FROM ranked r
        WHERE s.id = r.id AND r.rn > 1
        """
    )
    op.drop_index("uq_subscriptions_active_user", table_name="subscriptions")
    op.create_index(
        "uq_subscriptions_active_user",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('active', 'unpaid')"),
    )


def downgrade() -> None:
    # 対象行が縮む方向（active のみ）なので index の再作成は必ず成功する。
    # upgrade で cancelled に確定した行は戻さない。
    op.drop_index("uq_subscriptions_active_user", table_name="subscriptions")
    op.create_index(
        "uq_subscriptions_active_user",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
