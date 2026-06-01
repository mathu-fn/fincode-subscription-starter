from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, FincodeRateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _envelope(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"detail": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.info(
            "app_error",
            code=exc.code,
            path=str(request.url.path),
            method=request.method,
        )
        headers: dict[str, str] = {}
        if isinstance(exc, FincodeRateLimitError) and exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(exc.code, exc.message),
            headers=headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic / FastAPI バリデーションエラー: openapi.yml の ValidationError スキーマが
        # 約束する配列形式を維持する。``ctx`` は JSON 非対応の値（ValueError 等）を含む
        # 可能性があるため文字列に変換する。
        items = []
        for err in exc.errors():
            items.append(
                {
                    "loc": list(err.get("loc", ())),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", "value_error"),
                }
            )
        return JSONResponse(status_code=422, content={"detail": items})

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=_envelope("rate_limited", f"Too many requests: {exc.detail}"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            content = {"detail": detail}
        else:
            code = {
                401: "unauthenticated",
                403: "forbidden",
                404: "not_found",
                409: "conflict",
                422: "unprocessable",
            }.get(exc.status_code, "http_error")
            message = detail if isinstance(detail, str) else "HTTP error."
            content = _envelope(code, message)
        return JSONResponse(status_code=exc.status_code, content=content)
