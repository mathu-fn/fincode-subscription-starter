from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings


def create_access_token(
    subject: str | int, *, expires_in: timedelta | None = None
) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (expires_in or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        # exp / sub を必須にして、期限なし・主体なしのトークンを拒否する。
        # クレーム欠落は MissingRequiredClaimError（InvalidTokenError のサブクラス）
        # として送出され、呼び出し側の invalid_token ハンドリングに乗る。
        options={"require": ["exp", "sub"], "verify_exp": True, "verify_signature": True},
    )
