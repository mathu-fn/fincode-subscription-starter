from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import _key_func


def test_production_rejects_mock_mode() -> None:
    with pytest.raises(ValidationError, match="FINCODE_MODE=mock"):
        Settings(
            app_env="production",
            fincode_mode="mock",
            jwt_secret_key="test-secret-key-please-change-very-long-string",
            fincode_webhook_secret="test-webhook-secret",
        )


def test_production_rejects_default_secrets() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(app_env="production", jwt_secret_key="change-this-in-production")

    with pytest.raises(ValidationError, match="FINCODE_WEBHOOK_SECRET"):
        Settings(
            app_env="production",
            jwt_secret_key="test-secret-key-please-change-very-long-string",
            fincode_webhook_secret="change-me",
        )


def test_rate_limit_key_prefers_authenticated_user() -> None:
    request = SimpleNamespace(
        state=SimpleNamespace(user=SimpleNamespace(id=123)),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )

    assert _key_func(request) == "user:123"
