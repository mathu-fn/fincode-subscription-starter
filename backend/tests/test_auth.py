from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_register_returns_token_and_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "bob@example.com"
    assert body["user"]["name"] == "Bob"


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"name": "Bob", "email": "dup@example.com", "password": "supersecret123"}
    await client.post("/api/register", json=payload)
    response = await client.post("/api/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_already_registered"


async def test_register_validation_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/register",
        json={"name": "", "email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], list)


async def test_login_success(client: AsyncClient, registered_user: dict) -> None:
    response = await client.post(
        "/api/login",
        json={"email": registered_user["user"]["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_wrong_password(client: AsyncClient, registered_user: dict) -> None:
    response = await client.post(
        "/api/login",
        json={"email": registered_user["user"]["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


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

    rows = (await db_session.execute(select(AuditLog).where(AuditLog.event == "auth.logout"))).scalars().all()
    assert len(rows) >= 1
