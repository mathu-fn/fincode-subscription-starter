from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLogMiddleware
from app.core.rate_limit import limiter


def create_app() -> FastAPI:
    configure_logging()

    settings = get_settings()

    app = FastAPI(
        title="fincode Subscription OSS API",
        description="React フロントエンド向けの FastAPI バックエンドです。",
        version="0.1.0",
    )

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

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "backend"}

    # ルーターをここで登録する。関数内でインポートすることでマイグレーション時に
    # モデルが読み込まれる際の循環インポートを防ぐ。
    from app.api.routes import auth as auth_routes
    from app.api.routes import cards as card_routes
    from app.api.routes import subscriptions as subscription_routes
    from app.api.routes import webhooks as webhook_routes

    app.include_router(auth_routes.router)
    app.include_router(card_routes.router)
    app.include_router(subscription_routes.router)
    app.include_router(webhook_routes.router)

    return app


app = create_app()
