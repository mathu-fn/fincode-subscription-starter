"""ドメイン・連携層の例外階層。

各例外は安定した文字列 ``code`` を持ち、API 例外ハンドラーが
``{detail:{code,message}}`` エンベロープを構築するために使用する。
生の fincode レスポンスボディはクライアントへ返してはいけない。
先に ``FincodeApiError`` でラップすること。
"""

from __future__ import annotations


class AppError(Exception):
    """安定した API レスポンスに変換されるアプリケーションエラーの基底クラス。"""

    code: str = "app_error"
    http_status: int = 400
    default_message: str = "An application error occurred."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


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


# ---- Business rule errors -----------------------------------------------


class ActiveSubscriptionExistsError(AppError):
    code = "active_subscription_exists"
    http_status = 409
    default_message = "An active subscription already exists for this user."


class CardInUseError(AppError):
    code = "card_in_use"
    http_status = 409
    default_message = "The card is referenced by an active subscription."


class CardNotFoundError(AppError):
    code = "card_not_found"
    http_status = 404
    default_message = "The card does not exist."


class ExpiredCardError(AppError):
    code = "expired_card"
    http_status = 422
    default_message = "The card has expired."


class PlanUnavailableError(AppError):
    code = "plan_unavailable"
    http_status = 422
    default_message = "The selected plan is unavailable."


class SubscriptionNotFoundError(AppError):
    code = "subscription_not_found"
    http_status = 404
    default_message = "No active subscription was found."


class OwnershipError(AppError):
    code = "forbidden"
    http_status = 403
    default_message = "You cannot access this resource."


class InvalidCredentialsError(AppError):
    code = "invalid_credentials"
    http_status = 401
    default_message = "Invalid email or password."


class UnauthenticatedError(AppError):
    code = "unauthenticated"
    http_status = 401
    default_message = "Authentication is required."


class TokenExpiredError(AppError):
    code = "token_expired"
    http_status = 401
    default_message = "Token expired."


class InvalidTokenError(AppError):
    code = "invalid_token"
    http_status = 401
    default_message = "Invalid token."


class EmailAlreadyRegisteredError(AppError):
    code = "email_already_registered"
    http_status = 409
    default_message = "This email is already registered."


class WebhookSignatureError(AppError):
    code = "invalid_webhook_signature"
    http_status = 401
    default_message = "Webhook signature verification failed."
