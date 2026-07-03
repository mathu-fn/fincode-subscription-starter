"""シークレット / PII のリダクト処理。

構造化ログ（``app/core/logging.py``）と監査ログ（``app/services/audit_logger.py``）で
共有する。キー集合を分けると片方だけ更新される事故が起きるため、ここに一本化する。
"""

from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "card",
    "card_number",
    "pan",
    "cvc",
    "fincode_signature",
    "x-api-key",
    "api_key",
    "fincode_response",
    "secret",
}


def scrub(value: Any) -> Any:
    """辞書・リストを再帰的に走査し、機微キーの値を ``***`` に置換する。"""
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value
