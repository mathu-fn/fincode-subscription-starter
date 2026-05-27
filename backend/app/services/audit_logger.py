"""監査ログヘルパー。

監査行はビジネス操作と同じ ``AsyncSession`` 内に書き込まれるため、
成功・失敗が原子的に保たれる。``before`` / ``after`` にはリクエストボディ・
シークレット・トークンを含めてはいけない。呼び出し元は永続化された状態の
プレーンな辞書を渡すこと。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

_REDACT_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "card_number",
    "pan",
    "cvc",
    "fincode_response",
    "secret",
    "authorization",
    "api_key",
}


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("***" if k.lower() in _REDACT_KEYS else _scrub(v)) for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


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
            before=_scrub(before) if before is not None else None,
            after=_scrub(after) if after is not None else None,
        )
        session.add(log)


_default = AuditLogger()


def get_audit_logger() -> AuditLogger:
    return _default
