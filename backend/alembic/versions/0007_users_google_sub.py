"""add google_sub to users and make password_hash nullable

Google 認証(GIS ID トークン)への移行第一段。Google の subject 識別子を
一意キーとして保持する ``google_sub`` を追加する。unique index は NULL の
重複を許すため、Google 未連携の既存行はそのまま共存できる。

``password_hash`` は Google 経由で作成されるユーザーが値を持たないため
nullable へ緩和する（カラム自体の削除は次の revision 0008 で行う）。

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # password_hash が NULL の行（Google 経由で作成されたユーザー）が存在すると
    # NOT NULL への復元は失敗する。その場合は該当行を先に削除する必要がある。
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
