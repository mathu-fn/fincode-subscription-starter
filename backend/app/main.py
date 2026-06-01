from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.middleware import RequestLogMiddleware
from app.core.rate_limit import configure_limiter


def create_app() -> FastAPI:
    configure_logging()

    settings = get_settings()

    app = FastAPI(
        title="fincode Subscription OSS API",
        description="React フロントエンド向けの FastAPI バックエンドです。",
        version="0.1.0",
        lifespan=lifespan,
    )

    limiter = configure_limiter(settings)
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestLogMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    Instrumentator(
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, include_in_schema=False)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "backend"}

    from app.api.router import api_router

    app.include_router(api_router)

    return app


app = create_app()
