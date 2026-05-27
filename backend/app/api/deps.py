"""FastAPI 依存関係: DB セッション・現在ユーザー・fincode クライアント・監査ロガー。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.exceptions import InvalidCredentialsError
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
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Missing Authorization header."})
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Invalid Authorization header."})
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
        raise HTTPException(status_code=401, detail={"code": "token_expired", "message": "Token expired."}) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail={"code": "invalid_token", "message": "Invalid token."}) from e

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise InvalidCredentialsError("Invalid token subject.")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as e:
        raise InvalidCredentialsError("Invalid token subject.") from e

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "User not found."})
    return user


def get_fincode_client(settings: Settings = Depends(get_settings)) -> "FincodeClient":
    from app.services.fincode.client import FincodeHttpClient

    return FincodeHttpClient(
        base_url=settings.fincode_base_url,
        api_key=settings.fincode_api_key,
        tenant_shop_id=settings.fincode_tenant_shop_id or None,
    )


def get_audit_logger_dep() -> AuditLogger:
    return get_audit_logger()
