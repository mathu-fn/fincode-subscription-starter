"""FastAPI 依存関係: DB セッション・現在ユーザー・fincode クライアント・監査ロガー。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.exceptions import UnauthenticatedError
from app.core.security import decode_token
from app.services.audit_logger import AuditLogger, get_audit_logger

if TYPE_CHECKING:
    from app.models.user import User
    from app.services.fincode.client import FincodeClient


async def get_session() -> AsyncIterator[AsyncSession]:
    async for s in get_db():
        yield s


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise UnauthenticatedError("Missing Authorization header.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthenticatedError("Invalid Authorization header.")
    return token


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> "User":
    from app.models.user import User

    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as e:
        raise UnauthenticatedError(code="token_expired") from e
    except jwt.InvalidTokenError as e:
        raise UnauthenticatedError(code="invalid_token") from e

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise UnauthenticatedError("Invalid token subject.", code="invalid_credentials")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as e:
        raise UnauthenticatedError("Invalid token subject.", code="invalid_credentials") from e

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthenticatedError("User not found.")
    return user


def get_fincode_client(settings: Settings = Depends(get_settings)) -> "FincodeClient":
    if settings.fincode_mock_enabled:
        from app.services.fincode.mock_client import FincodeMockClient

        return FincodeMockClient()

    from app.services.fincode.client import FincodeHttpClient

    return FincodeHttpClient(
        base_url=settings.fincode_base_url,
        api_key=settings.fincode_api_key,
        tenant_shop_id=settings.fincode_tenant_shop_id or None,
    )


def get_audit_logger_dep() -> AuditLogger:
    return get_audit_logger()
