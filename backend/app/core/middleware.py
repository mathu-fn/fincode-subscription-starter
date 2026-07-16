"""リクエストログミドルウェア。

各リクエストのメソッド・パス・ステータス・レイテンシをログに記録する。
シークレットと PII は app.core.logging に設定した structlog プロセッサーが除去する。
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger("request")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """全レスポンスに保守的なセキュリティヘッダを付与する。

    ここは JSON API（+ Swagger UI）なので、CDN スクリプトを壊す厳格な CSP は
    付けない（SPA 本体の CSP はフロントの配信ホスト側の責務）。ここでは MIME
    スニッフィング抑止・クリックジャッキング防止・リファラ抑制のみを担う。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000.0
            logger.error(
                "request_failed",
                method=request.method,
                path=str(request.url.path),
                request_id=request_id,
                latency_ms=round(elapsed, 1),
            )
            raise
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.info(
            "request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            request_id=request_id,
            latency_ms=round(elapsed, 1),
        )
        response.headers["X-Request-ID"] = request_id
        return response
