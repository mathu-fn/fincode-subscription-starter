"""監査ログヘルパー。

監査行はビジネス操作と同じ ``AsyncSession`` 内に書き込まれるため、
成功・失敗が原子的に保たれる。``before`` / ``after`` にはリクエストボディ・
シークレット・トークンを含めてはいけない。呼び出し元は永続化された状態の
プレーンな辞書を渡すこと。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redaction import scrub


class AuditLogger:
    async def record(
        self,
        session: AsyncSession,
        *,
        user_id: int | None,
        event: str,
        auditable_type: str,
        auditable_id: int | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        # モデルのインポート順序を固定しないよう遅延インポートする。
        from app.models.audit_log import AuditLog

        log = AuditLog(
            user_id=user_id,
            event=event,
            auditable_type=auditable_type,
            auditable_id=auditable_id,
            before=scrub(before) if before is not None else None,
            after=scrub(after) if after is not None else None,
        )
        session.add(log)


_default = AuditLogger()


def get_audit_logger() -> AuditLogger:
    return _default
