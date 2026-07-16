from functools import lru_cache
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# 本番セーフティ検証を緩めてよいと明示的に宣言された開発/テスト環境の許可リスト。
# ここに無い値（"staging" / "production" / 未設定 / タイプミス）はすべて本番扱いにする。
# 「本番の許可リスト」ではなく「開発の許可リスト」で判定するのは、判定漏れを常に
# 安全側（strict）へ倒すため。
_DEV_ENVIRONMENTS = frozenset({"local", "dev", "development", "test", "testing"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 安全側デフォルト: 未設定なら "production"（strict）に倒す。既定を "local" に
    # すると、本番デプロイで APP_ENV の設定を忘れた瞬間に _validate_production_safety
    # が沈黙し（fail-open）、リポジトリにコミット済みの弱いデフォルト秘密鍵のまま
    # 起動してしまう。ローカル/テストは APP_ENV=local を明示すること。
    app_env: str = "production"
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://app:change-me@127.0.0.1:5432/subscription_app"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Google ID トークンの aud 検証に使う OAuth 2.0 クライアント ID。
    # フロントエンドの VITE_GOOGLE_CLIENT_ID と同一値でなければ全ログインが 401 になる。
    google_client_id: str = ""

    fincode_api_key: str = ""
    fincode_public_key: str = ""
    fincode_base_url: str = "https://api.test.fincode.jp"
    fincode_tenant_shop_id: str = ""
    fincode_webhook_secret: str = "change-me"
    # "mock" にすると fincode API を一切叩かず固定のダミーデータを返す。
    # fincode アカウント無しで UI / API を試すための開発専用モード。
    # 本番では既定の "live" のままにする（誤って mock で起動しないよう既定は安全側）。
    fincode_mode: str = "live"

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    rate_limit_storage_uri: str = "memory://"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def sync_database_url(self) -> str:
        """Alembic は同期ドライバーを使用する。+asyncpg を +psycopg に変換。"""
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def fincode_mock_enabled(self) -> bool:
        """fincode モッククライアントを使うべきか（``FINCODE_MODE=mock``）。"""
        return self.fincode_mode.strip().lower() == "mock"

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() not in _DEV_ENVIRONMENTS

    @model_validator(mode="after")
    def _validate_production_safety(self) -> Self:
        if not self.is_production:
            return self

        if self.fincode_mock_enabled:
            raise ValueError("FINCODE_MODE=mock is not allowed in production.")
        if self.jwt_secret_key.startswith("change-this-in-production"):
            raise ValueError("JWT_SECRET_KEY must be changed in production.")
        if self.fincode_webhook_secret == "change-me":
            raise ValueError("FINCODE_WEBHOOK_SECRET must be changed in production.")
        if not self.google_client_id:
            raise ValueError("GOOGLE_CLIENT_ID must be set in production.")
        if not self.fincode_api_key:
            raise ValueError("FINCODE_API_KEY must be set in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
