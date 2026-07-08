from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_password_login_endpoints_are_gone(client: AsyncClient) -> None:
    # メール+パスワード認証は廃止済み。ルート自体が存在しないことを固定する。
    register = await client.post(
        "/api/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "supersecret123"},
    )
    login = await client.post(
        "/api/login",
        json={"email": "bob@example.com", "password": "supersecret123"},
    )
    assert register.status_code == 404
    assert login.status_code == 404


async def test_token_missing_required_claims_rejected(client: AsyncClient) -> None:
    import jwt

    from app.core.config import get_settings

    settings = get_settings()
    # exp を欠いた（=失効しない）トークンは require=["exp"] により拒否される。
    forged = jwt.encode({"sub": "1"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    client.headers["Authorization"] = f"Bearer {forged}"
    response = await client.get("/api/user")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_session_status_with_token(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/session-status")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["email"] == "alice@example.com"


async def test_get_user_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/user")
    assert response.status_code == 401


async def test_get_user_with_invalid_token(client: AsyncClient) -> None:
    client.headers["Authorization"] = "Bearer this.is.invalid"
    response = await client.get("/api/user")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_logout_writes_audit_log(auth_client: AsyncClient, db_session) -> None:
    from sqlalchemy import select

    from app.models.audit_log import AuditLog

    response = await auth_client.post("/api/logout")
    assert response.status_code == 200

    rows = (
        (await db_session.execute(select(AuditLog).where(AuditLog.event == "auth.logout")))
        .scalars()
        .all()
    )
    # ちょうど 1 件（二重記録を見逃さない）。
    assert len(rows) == 1


# ---- Google ログイン ------------------------------------------------------
# Google の JWKS を自動テストで叩かないよう、検証済み ID（verify_id_token の
# 戻り値）を monkeypatch で差し替える。トークン検証ロジック自体のテストは
# 下の verify_id_token 単体テスト（_verify を差し替え）で行う。


def _stub_google_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "google-sub-1",
    email: str = "google.user@example.com",
    name: str = "Google User",
) -> None:
    from app.services.google_identity import GoogleIdentity

    async def fake_verify(credential: str) -> GoogleIdentity:
        return GoogleIdentity(sub=sub, email=email, name=name)

    monkeypatch.setattr("app.services.google_identity.verify_id_token", fake_verify)


async def test_google_login_creates_user_and_returns_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_google_identity(monkeypatch)
    response = await client.post("/api/auth/google", json={"credential": "fake-credential"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "google.user@example.com"
    assert body["user"]["name"] == "Google User"


async def test_google_login_is_idempotent_for_same_sub(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_google_identity(monkeypatch)
    first = await client.post("/api/auth/google", json={"credential": "fake-credential"})
    second = await client.post("/api/auth/google", json={"credential": "fake-credential"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


async def test_google_login_email_conflict_returns_409(
    client: AsyncClient, registered_user: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # 既存ユーザーと同じメールでも sub が異なる Google アカウントは紐付けない。
    _stub_google_identity(monkeypatch, email=registered_user["user"]["email"])
    response = await client.post("/api/auth/google", json={"credential": "fake-credential"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_already_registered"


async def test_google_login_invalid_token_returns_401(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.exceptions import UnauthenticatedError

    async def fake_verify(credential: str):
        raise UnauthenticatedError(code="invalid_google_token")

    monkeypatch.setattr("app.services.google_identity.verify_id_token", fake_verify)
    response = await client.post("/api/auth/google", json={"credential": "not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_google_token"


async def test_google_login_missing_credential_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/auth/google", json={})
    assert response.status_code == 422


async def test_google_login_token_grants_access(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_google_identity(monkeypatch)
    login = await client.post("/api/auth/google", json={"credential": "fake-credential"})
    token = login.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    me = await client.get("/api/user")
    assert me.status_code == 200
    assert me.json()["email"] == "google.user@example.com"


async def test_google_login_writes_audit_logs(
    client: AsyncClient, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import select

    from app.models.audit_log import AuditLog

    _stub_google_identity(monkeypatch)
    first = await client.post("/api/auth/google", json={"credential": "fake-credential"})
    assert first.status_code == 200

    async def events() -> list[str]:
        rows = (await db_session.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()
        return [row.event for row in rows]

    # 初回はユーザー作成の auth.register とログインの auth.login が両方入る。
    assert (await events()).count("auth.register") == 1
    assert (await events()).count("auth.login") == 1

    second = await client.post("/api/auth/google", json={"credential": "fake-credential"})
    assert second.status_code == 200

    # 2 回目以降は auth.login のみ増える。
    assert (await events()).count("auth.register") == 1
    assert (await events()).count("auth.login") == 2


# ---- verify_id_token 単体（Google 署名検証のみ差し替え） -------------------


def _stub_google_claims(monkeypatch: pytest.MonkeyPatch, claims: dict[str, Any]) -> None:
    from app.services import google_identity

    monkeypatch.setattr(google_identity, "_verify", lambda credential, client_id: claims)


async def test_verify_id_token_maps_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.google_identity import verify_id_token

    _stub_google_claims(
        monkeypatch,
        {
            "sub": "sub-123",
            "email": "  Mixed.Case@Example.COM ",
            "email_verified": True,
            "name": "Alice Example",
        },
    )
    identity = await verify_id_token("fake-credential")
    assert identity.sub == "sub-123"
    assert identity.email == "mixed.case@example.com"
    assert identity.name == "Alice Example"


async def test_verify_id_token_falls_back_to_email_local_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.google_identity import verify_id_token

    _stub_google_claims(
        monkeypatch,
        {"sub": "sub-123", "email": "alice@example.com", "email_verified": True},
    )
    identity = await verify_id_token("fake-credential")
    assert identity.name == "alice"


async def test_verify_id_token_rejects_unverified_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import UnauthenticatedError
    from app.services.google_identity import verify_id_token

    _stub_google_claims(
        monkeypatch,
        {"sub": "sub-123", "email": "alice@example.com", "email_verified": False},
    )
    with pytest.raises(UnauthenticatedError) as exc_info:
        await verify_id_token("fake-credential")
    assert exc_info.value.code == "google_email_not_verified"


async def test_verify_id_token_rejects_missing_sub_or_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import UnauthenticatedError
    from app.services.google_identity import verify_id_token

    for claims in (
        {"email": "alice@example.com", "email_verified": True},  # sub 欠落
        {"sub": "sub-123", "email_verified": True},  # email 欠落
    ):
        _stub_google_claims(monkeypatch, claims)
        with pytest.raises(UnauthenticatedError) as exc_info:
            await verify_id_token("fake-credential")
        assert exc_info.value.code == "invalid_google_token"


async def test_verify_id_token_translates_verification_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import UnauthenticatedError
    from app.services import google_identity
    from app.services.google_identity import verify_id_token

    def raise_value_error(credential: str, client_id: str) -> dict[str, Any]:
        raise ValueError("Token expired")

    monkeypatch.setattr(google_identity, "_verify", raise_value_error)
    with pytest.raises(UnauthenticatedError) as exc_info:
        await verify_id_token("expired-token")
    assert exc_info.value.code == "invalid_google_token"
