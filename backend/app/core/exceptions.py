"""ドメイン・連携層の例外階層。

各例外は安定した文字列 ``code`` を持ち、API 例外ハンドラーが
``{detail:{code,message}}`` エンベロープを構築するために使用する。
生の fincode レスポンスボディはクライアントへ返してはいけない。
先に ``FincodeApiError`` でラップすること。
"""

from __future__ import annotations

from app.core.error_codes import ERROR_DEFAULTS


class AppError(Exception):
    """安定した API レスポンスに変換されるアプリケーションエラーの基底クラス。"""

    code: str = "app_error"
    http_status: int = 400
    default_message: str = "An application error occurred."

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        if code is not None:
            self.code = code
        resolved = message or ERROR_DEFAULTS.get(self.code, self.default_message)
        super().__init__(resolved)
        self.message = resolved


# ---- Fincode integration errors -----------------------------------------


class FincodeApiError(AppError):
    code = "fincode_api_error"
    http_status = 502
    default_message = "Failed to communicate with the payment service."


class FincodeRateLimitError(FincodeApiError):
    code = "fincode_rate_limited"
    http_status = 429
    default_message = "The payment service is rate limiting requests."

    def __init__(self, message: str | None = None, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class FincodeServerError(FincodeApiError):
    code = "fincode_server_error"
    http_status = 503
    default_message = "The payment service returned an error."


class FincodeTimeoutError(FincodeApiError):
    code = "fincode_timeout"
    http_status = 504
    default_message = "Timed out talking to the payment service."


class CircuitBreakerOpenError(FincodeApiError):
    code = "fincode_unavailable"
    http_status = 503
    default_message = "The payment service is temporarily unavailable."


# ---- Generic error categories -------------------------------------------


class NotFoundError(AppError):
    code = "not_found"
    http_status = 404
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    code = "conflict"
    http_status = 409
    default_message = "The request conflicts with the current state."


class UnprocessableError(AppError):
    code = "unprocessable"
    http_status = 422
    default_message = "The request could not be processed."


class ForbiddenError(AppError):
    code = "forbidden"
    http_status = 403
    default_message = "You cannot access this resource."


class UnauthenticatedError(AppError):
    code = "unauthenticated"
    http_status = 401
    default_message = "Authentication is required."
