"""Test fixtures.

Boots a PostgreSQL container once per session, runs Alembic migrations against
it, exposes an ``AsyncClient`` bound to the FastAPI app, and resets the slowapi
rate limiter between tests so individual tests are independent.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any, cast

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

# Set env BEFORE app modules import the settings.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-please-change-very-long-string")
os.environ.setdefault("FINCODE_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    container = PostgresContainer("postgres:16-alpine", username="app", password="change-me", dbname="subscription_app")
    container.start()
    try:
        yield container
    finally:
        container.stop()


def _async_url_from(container: PostgresContainer) -> str:
    raw = cast(str, container.get_connection_url())
    # testcontainers may use psycopg2 or psycopg as the driver suffix
    for old in ("+psycopg2", "+psycopg"):
        raw = raw.replace(old, "+asyncpg")
    if "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


def _sync_url_from(container: PostgresContainer) -> str:
    raw = cast(str, container.get_connection_url())
    if "+asyncpg" in raw:
        raw = raw.replace("+asyncpg", "+psycopg")
    elif "+psycopg2" in raw:
        raw = raw.replace("+psycopg2", "+psycopg")
    elif "+psycopg" in raw:
        pass
    else:
        raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw


@pytest.fixture(scope="session")
def applied_migrations(postgres_container: PostgresContainer) -> str:
    """Run Alembic migrations against the test container. Returns async URL."""

    sync_url = _sync_url_from(postgres_container)
    async_url = _async_url_from(postgres_container)
    os.environ["DATABASE_URL"] = async_url
    # Clear the lru_cache so app.core.config picks up the new URL.
    from app.core.config import get_settings

    get_settings.cache_clear()

    from alembic.config import Config

    from alembic import command

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    cfg.set_main_option("script_location", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic")))
    command.upgrade(cfg, "head")
    return async_url


@pytest_asyncio.fixture()
async def db_engine(applied_migrations: str) -> AsyncIterator[Any]:
    engine = create_async_engine(applied_migrations, future=True, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(app_instance: Any, db_engine: Any) -> AsyncIterator[AsyncSession]:
    # Depend on app_instance so the per-test truncate has already run before
    # the test reads the DB.
    Session = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False, class_=AsyncSession)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def app_instance(db_engine: Any) -> AsyncIterator[Any]:
    # Reset rate limiter storage so test order does not exhaust 5/minute limits.
    from app.core.rate_limit import get_limiter
    from app.main import app

    get_limiter().reset()

    # Truncate all application tables so tests do not see leftover state.
    from sqlalchemy import text

    from app.models import Base

    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))

    async with app.router.lifespan_context(app):
        yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client(app_instance) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture()
async def registered_user(client: AsyncClient) -> dict[str, Any]:
    payload = {
        "name": "Test User",
        "email": "alice@example.com",
        "password": "supersecret123",
    }
    response = await client.post("/api/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    return {"token": data["access_token"], "user": data["user"], "password": payload["password"]}


@pytest_asyncio.fixture()
async def auth_client(client: AsyncClient, registered_user: dict[str, Any]) -> AsyncClient:
    client.headers.update({"Authorization": f"Bearer {registered_user['token']}"})
    return client
