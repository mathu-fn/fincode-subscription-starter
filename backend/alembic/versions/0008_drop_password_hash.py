"""drop users.password_hash

Google 認証への一新に伴いメール+パスワードログインを廃止したため、
argon2 ハッシュを DB に残しておく理由がなくなった（負債になるだけ）。

downgrade はカラムを nullable で再作成するのみで、ハッシュ値は復元できない
（不可逆）。パスワードログインへ戻す場合は全ユーザーの再登録が必要になる。

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    # データは戻らない。旧 NOT NULL 制約も復元しない（全行 NULL になるため）。
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
