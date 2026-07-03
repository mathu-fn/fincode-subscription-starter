from __future__ import annotations

from typing import Any

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import Settings, get_settings


def _key_func(request: Any) -> str:
    # JWT でユーザーを特定できる場合はユーザー ID を優先し、認証済みトラフィックを
    # ユーザーごとにレート制限する。それ以外はリモートアドレスにフォールバック。
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"
    return get_remote_address(request)


def create_limiter(settings: Settings) -> Limiter:
    return Limiter(
        key_func=_key_func,
        storage_uri=settings.rate_limit_storage_uri,
        default_limits=[],
        headers_enabled=False,
    )


# import 時に一度だけ生成するシングルトン。slowapi のデコレータはデコレート時の
# インスタンスを閉じ込め、ミドルウェアは app.state.limiter を参照するため、
# 両者が常に同一インスタンスを共有している必要がある。
limiter: Limiter = create_limiter(get_settings())


def get_limiter() -> Limiter:
    return limiter
