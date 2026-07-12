"""FastAPI 依存関係: DB セッション・現在ユーザー・fincode クライアント・監査ロガー。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthenticatedError
from app.core.security import decode_token
from app.models.user import User
from app.services.audit_logger import AuditLogger, get_audit_logger
from app.services.card_manager import CardManager
from app.services.fincode.client import FincodeClient
from app.services.subscription_manager import SubscriptionManager
from app.services.webhook_handler import FincodeWebhookHandler

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = cast(
        async_sessionmaker[AsyncSession] | None,
        getattr(request.app.state, "db_sessionmaker", None),
    )
    if sessionmaker is None:
        raise RuntimeError("Database sessionmaker is not initialized.")

    async with sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _extract_bearer(credentials: HTTPAuthorizationCredentials | None) -> str:
    # HTTPBearer(auto_error=False) は scheme が bearer かつ値が非空のときだけ
    # credentials を返すため、None チェックだけで十分。
    if credentials is None:
        raise UnauthenticatedError("Missing Authorization header.")
    return credentials.credentials


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: SessionDep,
) -> User:
    token = _extract_bearer(credentials)
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as e:
        raise UnauthenticatedError(code="token_expired") from e
    except jwt.InvalidTokenError as e:
        raise UnauthenticatedError(code="invalid_token") from e

    # decode_token が sub を必須クレームにしているため存在は保証済み。
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as e:
        raise UnauthenticatedError("Invalid token subject.", code="invalid_credentials") from e

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthenticatedError("User not found.")
    request.state.user = user
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_fincode_client(request: Request) -> FincodeClient:
    client = cast(FincodeClient | None, getattr(request.app.state, "fincode_client", None))
    if client is None:
        raise RuntimeError("fincode client is not initialized.")
    return client


FincodeClientDep = Annotated[FincodeClient, Depends(get_fincode_client)]


def get_audit_logger_dep() -> AuditLogger:
    return get_audit_logger()


AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger_dep)]


def get_card_manager(
    client: FincodeClientDep,
    audit: AuditLoggerDep,
) -> CardManager:
    return CardManager(client, audit=audit)


CardManagerDep = Annotated[CardManager, Depends(get_card_manager)]


def get_subscription_manager(
    client: FincodeClientDep,
    audit: AuditLoggerDep,
) -> SubscriptionManager:
    return SubscriptionManager(client, audit=audit)


SubscriptionManagerDep = Annotated[SubscriptionManager, Depends(get_subscription_manager)]


def get_webhook_handler(
    settings: SettingsDep,
    audit: AuditLoggerDep,
) -> FincodeWebhookHandler:
    return FincodeWebhookHandler(secret=settings.fincode_webhook_secret, audit=audit)


WebhookHandlerDep = Annotated[FincodeWebhookHandler, Depends(get_webhook_handler)]
