from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthenticatedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut


async def register(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError(code="email_already_registered")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate(db: AsyncSession, payload: LoginRequest) -> User:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthenticatedError(code="invalid_credentials")
    return user


def issue_token(user: User) -> AuthResponse:
    token, expires_at = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
        user=UserOut.model_validate(user),
    )
