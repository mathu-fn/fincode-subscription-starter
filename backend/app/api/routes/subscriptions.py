from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, status

from app.api.deps import (
    CurrentUserDep,
    SessionDep,
    SubscriptionManagerDep,
)
from app.core.rate_limit import limiter
from app.schemas.subscription import (
    BillingHistoryItem,
    ChangeSubscriptionPlanRequest,
    CreateSubscriptionRequest,
    PaginatedBillingHistory,
    PlanOut,
    SubscriptionOut,
)

router = APIRouter(prefix="/subscription", tags=["subscriptions"])

# クライアント提供の Idempotency-Key ヘッダー。POST / PATCH で同じ制約を共有する。
IdempotencyKeyHeader = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=1, max_length=64)
]


@router.get("", response_model=SubscriptionOut | None)
@limiter.limit("60/minute")
async def get_subscription(
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
    manager: SubscriptionManagerDep,
) -> SubscriptionOut | None:
    sub = await manager.get_active(db, user)
    if sub is None:
        return None
    return SubscriptionOut.model_validate(sub)


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_subscription(
    request: Request,
    payload: CreateSubscriptionRequest,
    db: SessionDep,
    user: CurrentUserDep,
    manager: SubscriptionManagerDep,
    idempotency_key: IdempotencyKeyHeader = None,
) -> SubscriptionOut:
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


@router.patch("", response_model=SubscriptionOut)
@limiter.limit("5/minute")
async def change_subscription_plan(
    request: Request,
    payload: ChangeSubscriptionPlanRequest,
    db: SessionDep,
    user: CurrentUserDep,
    manager: SubscriptionManagerDep,
    idempotency_key: IdempotencyKeyHeader = None,
) -> SubscriptionOut:
    sub = await manager.change_plan(
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
    db: SessionDep,
    user: CurrentUserDep,
    manager: SubscriptionManagerDep,
) -> SubscriptionOut:
    sub = await manager.cancel(db, user)
    await db.commit()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)


@router.get("/plans", response_model=list[PlanOut])
@limiter.limit("60/minute")
async def list_plans(
    request: Request,
    user: CurrentUserDep,
    manager: SubscriptionManagerDep,
) -> list[PlanOut]:
    plans = await manager.list_plans()
    return [PlanOut.model_validate(p) for p in plans]


@router.get("/history", response_model=PaginatedBillingHistory)
@limiter.limit("60/minute")
async def list_history(
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
    manager: SubscriptionManagerDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedBillingHistory:
    rows, total = await manager.list_history(db, user, page=page, per_page=per_page)
    return PaginatedBillingHistory(
        data=[BillingHistoryItem.model_validate(r) for r in rows],
        page=page,
        per_page=per_page,
        total=total,
    )
