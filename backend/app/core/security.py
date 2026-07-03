from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    # ミスマッチ・不正な argon2 ハッシュは pwdlib が False を返す。例外になるのは
    # ハッシュ形式自体を識別できない場合のみで、これも認証失敗として扱う。
    try:
        return _password_hash.verify(plain, hashed)
    except UnknownHashError:
        return False


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
