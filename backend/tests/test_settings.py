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


def test_unset_app_env_is_treated_as_production(monkeypatch: pytest.MonkeyPatch) -> None:
    # fail-open 回帰防止: APP_ENV 未指定（=デフォルト）でも本番扱いになり、
    # コミット済みの弱いデフォルト JWT 秘密鍵での起動を拒否する。
    # conftest の APP_ENV=local 環境変数と backend/.env の APP_ENV の両方を無効化し、
    # モデル既定値そのものの挙動を検証する。
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(jwt_secret_key="change-this-in-production", _env_file=None)


def test_unknown_app_env_is_treated_as_production() -> None:
    # タイプミスや "staging" など未知の値も安全側（本番扱い）に倒す。
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(app_env="staging", jwt_secret_key="change-this-in-production")

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(app_env="prodcution", jwt_secret_key="change-this-in-production")


def test_explicit_dev_env_allows_relaxed_config() -> None:
    # 明示的な開発環境では弱い秘密鍵・モックモードを許容する（ローカル開発の利便性）。
    settings = Settings(
        app_env="local",
        jwt_secret_key="change-this-in-production",
        fincode_webhook_secret="change-me",
        fincode_mode="mock",
    )
    assert settings.is_production is False


def test_production_requires_google_client_id() -> None:
    with pytest.raises(ValidationError, match="GOOGLE_CLIENT_ID"):
        Settings(
            app_env="production",
            jwt_secret_key="test-secret-key-please-change-very-long-string",
            fincode_webhook_secret="test-webhook-secret",
            google_client_id="",
        )


def test_rate_limit_key_prefers_authenticated_user() -> None:
    request = SimpleNamespace(
        state=SimpleNamespace(user=SimpleNamespace(id=123)),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )

    assert _key_func(request) == "user:123"
