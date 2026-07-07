from fastapi import APIRouter, Request

from app.api.deps import AuditLoggerDep, CurrentUserDep, SessionDep
from app.core.rate_limit import limiter
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    MessageResponse,
    SessionStatusResponse,
    UserOut,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/google", response_model=AuthResponse)
@limiter.limit("5/minute")
async def google_login(
    request: Request,
    payload: GoogleLoginRequest,
    db: SessionDep,
    audit: AuditLoggerDep,
) -> AuthResponse:
    user, created = await auth_service.login_with_google(db, payload.credential)
    if created:
        await audit.record(
            db,
            user_id=user.id,
            event="auth.register",
            auditable_type="user",
            auditable_id=user.id,
            after={"email": user.email, "name": user.name},
        )
    await audit.record(
        db,
        user_id=user.id,
        event="auth.login",
        auditable_type="user",
        auditable_id=user.id,
        after={"method": "google"},
    )
    await db.commit()
    if created:
        # created_at などのサーバー既定値を issue_token が参照できるよう読み直す。
        await db.refresh(user)
    return auth_service.issue_token(user)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("60/minute")
async def logout(
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
    audit: AuditLoggerDep,
) -> MessageResponse:
    await audit.record(
        db,
        user_id=user.id,
        event="auth.logout",
        auditable_type="user",
        auditable_id=user.id,
    )
    await db.commit()
    return MessageResponse(message="Logged out.")


@router.get("/session-status", response_model=SessionStatusResponse)
@limiter.limit("60/minute")
async def session_status(
    request: Request,
    user: CurrentUserDep,
) -> SessionStatusResponse:
    return SessionStatusResponse(authenticated=True, user=UserOut.model_validate(user))


@router.get("/user", response_model=UserOut)
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user: CurrentUserDep,
) -> UserOut:
    return UserOut.model_validate(user)
