from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_audit_logger_dep,
    get_current_user,
    get_fincode_client,
    get_session,
)
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.subscription import (
    BillingHistoryItem,
    CreateSubscriptionRequest,
    PaginatedBillingHistory,
    PlanOut,
    SubscriptionOut,
)
from app.services.audit_logger import AuditLogger
from app.services.fincode.client import FincodeClient
from app.services.subscription_manager import SubscriptionManager

router = APIRouter(prefix="/api/subscription", tags=["subscriptions"])


@router.get("", response_model=SubscriptionOut | None)
@limiter.limit("60/minute")
async def get_subscription(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
) -> SubscriptionOut | None:
    manager = SubscriptionManager(client)
    sub = await manager.get_active(db, user)
    if sub is None:
        return None
    return SubscriptionOut.model_validate(sub)


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_subscription(
    request: Request,
    payload: CreateSubscriptionRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
    audit: AuditLogger = Depends(get_audit_logger_dep),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=64),
) -> SubscriptionOut:
    manager = SubscriptionManager(client, audit=audit)
    sub = await manager.subscribe(
        db,
        user,
        plan_id=payload.fincode_plan_id,
        card_id=payload.card_id,
        idempotency_key=idempotency_key,
    )
    await db.commit()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)


@router.delete("", response_model=SubscriptionOut)
@limiter.limit("5/minute")
async def cancel_subscription(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
    audit: AuditLogger = Depends(get_audit_logger_dep),
) -> SubscriptionOut:
    manager = SubscriptionManager(client, audit=audit)
    sub = await manager.cancel(db, user)
    await db.commit()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)


@router.get("/plans", response_model=list[PlanOut])
@limiter.limit("60/minute")
async def list_plans(
    request: Request,
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
) -> list[PlanOut]:
    manager = SubscriptionManager(client)
    plans = await manager.list_plans()
    return [
        PlanOut(
            fincode_plan_id=p["fincode_plan_id"],
            name=p["name"],
            amount=p["amount"],
            currency=p.get("currency", "JPY"),
            interval=p["interval"],
        )
        for p in plans
    ]


@router.get("/history", response_model=PaginatedBillingHistory)
@limiter.limit("60/minute")
async def list_history(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
) -> PaginatedBillingHistory:
    manager = SubscriptionManager(client)
    rows, total = await manager.list_history(db, user, page=page, per_page=per_page)
    return PaginatedBillingHistory(
        data=[BillingHistoryItem.model_validate(r) for r in rows],
        page=page,
        per_page=per_page,
        total=total,
    )
