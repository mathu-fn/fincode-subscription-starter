from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "local"
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://app:change-me@127.0.0.1:5432/subscription_app"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    fincode_api_key: str = ""
    fincode_public_key: str = ""
    fincode_base_url: str = "https://api.test.fincode.jp"
    fincode_tenant_shop_id: str = ""
    fincode_webhook_secret: str = "change-me"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
