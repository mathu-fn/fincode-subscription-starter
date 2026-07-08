"""Pin the business error-code contract: code / http_status / message."""

from __future__ import annotations

import pytest

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthenticatedError,
    UnprocessableError,
)


@pytest.mark.parametrize(
    ("exc", "expected_code", "expected_status", "expected_message"),
    [
        (
            NotFoundError(code="card_not_found"),
            "card_not_found",
            404,
            "The card does not exist.",
        ),
        (
            NotFoundError(code="subscription_not_found"),
            "subscription_not_found",
            404,
            "No active subscription was found.",
        ),
        (
            ForbiddenError(),
            "forbidden",
            403,
            "You cannot access this resource.",
        ),
        (
            ConflictError(code="active_subscription_exists"),
            "active_subscription_exists",
            409,
            "An active subscription already exists for this user.",
        ),
        (
            ConflictError(code="subscription_cancel_scheduled"),
            "subscription_cancel_scheduled",
            409,
            "The subscription is already scheduled for cancellation.",
        ),
        (
            ConflictError(code="card_in_use"),
            "card_in_use",
            409,
            "The card is referenced by an active subscription.",
        ),
        (
            ConflictError(code="email_already_registered"),
            "email_already_registered",
            409,
            "This email is already registered.",
        ),
        (
            UnprocessableError(code="expired_card"),
            "expired_card",
            422,
            "The card has expired.",
        ),
        (
            UnprocessableError(code="card_required"),
            "card_required",
            422,
            "A card is required to subscribe to a paid plan.",
        ),
        (
            UnprocessableError(code="plan_unavailable"),
            "plan_unavailable",
            422,
            "The selected plan is unavailable.",
        ),
        (
            UnauthenticatedError(code="invalid_credentials"),
            "invalid_credentials",
            401,
            "Invalid email or password.",
        ),
        (
            UnauthenticatedError(),
            "unauthenticated",
            401,
            "Authentication is required.",
        ),
        (
            UnauthenticatedError(code="token_expired"),
            "token_expired",
            401,
            "Token expired.",
        ),
        (
            UnauthenticatedError(code="invalid_token"),
            "invalid_token",
            401,
            "Invalid token.",
        ),
        (
            UnauthenticatedError(code="invalid_webhook_signature"),
            "invalid_webhook_signature",
            401,
            "Webhook signature verification failed.",
        ),
        (
            UnprocessableError(code="invalid_webhook_payload"),
            "invalid_webhook_payload",
            422,
            "Webhook payload is malformed or missing required fields.",
        ),
    ],
)
def test_business_error_contract(
    exc: AppError,
    expected_code: str,
    expected_status: int,
    expected_message: str,
) -> None:
    assert exc.code == expected_code
    assert exc.http_status == expected_status
    assert exc.message == expected_message
    assert str(exc) == expected_message
