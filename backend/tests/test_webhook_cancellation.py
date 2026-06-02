from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.services.fincode.webhook_handler import FincodeWebhookHandler

WEBHOOK_SECRET = "test-webhook-secret"


def _signed_payload(payload: dict[str, Any]) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


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

    payload, signature = _signed_payload(
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

    payload, signature = _signed_payload(
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
