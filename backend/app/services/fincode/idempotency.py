"""決定論的な Idempotency-Key の生成。

fincode の書き込み API は ``Idempotency-Key`` ヘッダーを受け付ける。
リトライ時に同じキーを再利用することで、ネットワーク障害やワーカー再起動を跨いで
顧客・カード・契約の重複作成を防ぐ。
"""

from __future__ import annotations

import hashlib
import uuid


def idem_key(*parts: object) -> str:
    return ":".join(str(p) for p in parts if p is not None)


def token_fingerprint(token: str, length: int = 16) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:length]


def new_nonce() -> str:
    return uuid.uuid4().hex
