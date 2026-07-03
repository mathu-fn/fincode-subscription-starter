from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.db import create_db_engine, create_sessionmaker
from app.core.logging import get_logger
from app.services.fincode.client import FincodeClient, FincodeHttpClient
from app.services.fincode.mock_client import FincodeMockClient


def create_fincode_client(settings: Settings) -> FincodeClient:
    if settings.fincode_mock_enabled:
        return FincodeMockClient()

    return FincodeHttpClient(
        base_url=settings.fincode_base_url,
        api_key=settings.fincode_api_key,
        tenant_shop_id=settings.fincode_tenant_shop_id or None,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings

    engine = create_db_engine(settings.database_url)
    app.state.db_engine = engine
    app.state.db_sessionmaker = create_sessionmaker(engine)

    fincode_client = create_fincode_client(settings)
    app.state.fincode_client = fincode_client

    if settings.fincode_mock_enabled:
        get_logger("app.startup").warning(
            "fincode_mock_mode_enabled",
            detail="FINCODE_MODE=mock: 実際の fincode API は呼び出されません(開発用)。",
        )

    try:
        yield
    finally:
        await fincode_client.aclose()
        await engine.dispose()
