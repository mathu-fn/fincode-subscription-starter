from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.services.subscription_periods import as_utc
from app.services.webhook_handler import FincodeWebhookHandler
from tests.conftest import WEBHOOK_SECRET, signed_payload


async def test_webhook_cancellation_preserves_future_period(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    sub = Subscription(
        user_id=registered_user["user"]["id"],
        fincode_subscription_id="sub_webhook_future",
        nonce="nonce-future",
        fincode_plan_id="plan_test_pro",
        plan_name="Pro",
        plan_amount=500,
        plan_interval="month",
        status=SubscriptionStatus.ACTIVE,
        current_period_end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(sub)
    await db_session.commit()

    payload, signature = signed_payload(
        {
            "event_id": "evt_cancel_future",
            "event": "subscription.canceled",
            "data": {"subscription_id": "sub_webhook_future"},
        }
    )
    await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
        payload=payload, signature=signature, db=db_session
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.cancelled_at is not None


async def test_webhook_cancellation_expires_without_future_period(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    sub = Subscription(
        user_id=registered_user["user"]["id"],
        fincode_subscription_id="sub_webhook_elapsed",
        nonce="nonce-elapsed",
        fincode_plan_id="plan_test_pro",
        plan_name="Pro",
        plan_amount=500,
        plan_interval="month",
        status=SubscriptionStatus.ACTIVE,
        current_period_end=datetime(2000, 1, 1, tzinfo=UTC),
    )
    db_session.add(sub)
    await db_session.commit()

    payload, signature = signed_payload(
        {
            "event_id": "evt_cancel_elapsed",
            "event": "subscription.canceled",
            "data": {"subscription_id": "sub_webhook_elapsed"},
        }
    )
    await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
        payload=payload, signature=signature, db=db_session
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.CANCELLED
    assert sub.cancelled_at is not None


async def test_webhook_cancellation_does_not_shrink_future_period(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    # 解約 Webhook が解約発効日（``stop_date``）や前倒しの ``next_charge_date`` を
    # 返しても、subscribe 時に確定した未来の支払い済み期限を縮めてはならない。
    future = datetime(2099, 1, 1, tzinfo=UTC)
    sub = Subscription(
        user_id=registered_user["user"]["id"],
        fincode_subscription_id="sub_webhook_noshrink",
        nonce="nonce-noshrink",
        fincode_plan_id="plan_test_pro",
        plan_name="Pro",
        plan_amount=500,
        plan_interval="month",
        status=SubscriptionStatus.ACTIVE,
        current_period_end=future,
    )
    db_session.add(sub)
    await db_session.commit()

    payload, signature = signed_payload(
        {
            "event_id": "evt_cancel_noshrink",
            "event": "subscription.canceled",
            "data": {
                "subscription_id": "sub_webhook_noshrink",
                # 解約発効日（過去・現在）はキャンセル応答に載りうる。
                "stop_date": "2020/01/01 00:00:00.000",
                "next_charge_date": "2020/01/01 00:00:00.000",
            },
        }
    )
    await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
        payload=payload, signature=signature, db=db_session
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.cancelled_at is not None
    # 期限は縮まず 2099 のまま（期間末解約が維持される）。
    assert sub.current_period_end is not None
    assert as_utc(sub.current_period_end) == future
