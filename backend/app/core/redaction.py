"""シークレット / PII のリダクト処理。

構造化ログ（``app/core/logging.py``）と監査ログ（``app/services/audit_logger.py``）で
共有する。キー集合を分けると片方だけ更新される事故が起きるため、ここに一本化する。
"""

from __future__ import annotations

from typing import Any

# 照合はキー名の小文字完全一致（scrub 参照）。部分一致にしないのは
# "card_brand" のような非機微キーの巻き添えを避けるため。新しい機微フィールドを
# schema に足すときは、そのフィールド名をここにも追加すること。
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
    # Google ID トークン（GoogleLoginRequest.credential）。JWT そのもの。
    "credential",
    "id_token",
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
