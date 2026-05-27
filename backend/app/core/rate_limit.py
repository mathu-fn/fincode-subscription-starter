from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def _key_func(request) -> str:  # type: ignore[no-untyped-def]
    # JWT でユーザーを特定できる場合はユーザー ID を優先し、認証済みトラフィックを
    # ユーザーごとにレート制限する。それ以外はリモートアドレスにフォールバック。
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    storage_uri=settings.rate_limit_storage_uri,
    default_limits=[],
    headers_enabled=False,
)
