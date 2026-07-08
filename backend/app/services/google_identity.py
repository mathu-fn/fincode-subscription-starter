"""Google ID トークン（GIS credential）の検証。

フロントエンドの Google Identity Services ボタンが返す ID トークンを検証し、
アプリが必要とする最小限の属性（sub / email / name）へ写像する。
署名・exp・iss・aud の検証は google-auth の ``verify_oauth2_token`` が行い、
ここでは追加で ``email_verified`` を要求する。

検証は JWKS 取得のため同期 HTTP（requests）を伴う。イベントループを塞がない
よう ``run_in_threadpool`` でラップする（外部 HTTP は services 層に閉じ込める
規約もここで満たす）。credential はトークンそのものなのでログに出さないこと。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.concurrency import run_in_threadpool
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import get_settings
from app.core.exceptions import UnauthenticatedError
from app.schemas.auth import normalize_email

# JWKS フェッチ用の transport は毎回生成せず再利用する。
_transport_request = google_requests.Request()

# NTP ずれ等で iat が僅かに未来のトークンが散発的に落ちるのを防ぐ許容秒数。
_CLOCK_SKEW_SECONDS = 10


@dataclass(frozen=True)
class GoogleIdentity:
    """検証済み ID トークンから抽出した、アプリが使う属性のみの写像。"""

    sub: str
    email: str
    name: str


def _verify(credential: str, client_id: str) -> dict[str, Any]:
    # google-auth は py.typed だがこの関数は未型付け（Any 扱い）のため限定的に無視する。
    claims: dict[str, Any] = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
        credential,
        _transport_request,
        client_id,
        clock_skew_in_seconds=_CLOCK_SKEW_SECONDS,
    )
    return claims


async def verify_id_token(credential: str) -> GoogleIdentity:
    settings = get_settings()
    try:
        claims = await run_in_threadpool(_verify, credential, settings.google_client_id)
    except (ValueError, GoogleAuthError) as e:
        # 失敗理由（期限切れ・aud 不一致・署名不正など）はクライアントに開示しない。
        raise UnauthenticatedError(code="invalid_google_token") from e

    if not claims.get("email_verified"):
        raise UnauthenticatedError(code="google_email_not_verified")

    sub = claims.get("sub")
    email_raw = claims.get("email")
    if not sub or not email_raw:
        raise UnauthenticatedError(code="invalid_google_token")

    email = normalize_email(str(email_raw))
    name = str(claims.get("name") or "").strip() or email.split("@", 1)[0]
    return GoogleIdentity(sub=str(sub), email=email, name=name)
