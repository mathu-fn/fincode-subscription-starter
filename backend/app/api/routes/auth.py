from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_logger_dep, get_current_user, get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    SessionStatusResponse,
    UserOut,
)
from app.services import auth_service
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_session),
    audit: AuditLogger = Depends(get_audit_logger_dep),
) -> AuthResponse:
    user = await auth_service.register(db, payload)
    await audit.record(
        db,
        user_id=user.id,
        event="auth.register",
        auditable_type="user",
        auditable_id=user.id,
        after={"email": user.email, "name": user.name},
    )
    await db.commit()
    await db.refresh(user)
    return auth_service.issue_token(user)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await auth_service.authenticate(db, payload)
    return auth_service.issue_token(user)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("60/minute")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger_dep),
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
    user: User = Depends(get_current_user),
) -> SessionStatusResponse:
    return SessionStatusResponse(authenticated=True, user=UserOut.model_validate(user))


@router.get("/user", response_model=UserOut)
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user: User = Depends(get_current_user),
) -> UserOut:
    return UserOut.model_validate(user)
