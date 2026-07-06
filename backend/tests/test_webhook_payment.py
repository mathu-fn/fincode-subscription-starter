from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select

from app.core.enums import PaymentStatus, SubscriptionStatus
from app.core.exceptions import UnprocessableError
from app.models.subscription import Subscription
from app.models.subscription_result import SubscriptionResult
from app.services.fincode.webhook_handler import FincodeWebhookHandler
from app.services.subscription_periods import as_utc

WEBHOOK_SECRET = "test-webhook-secret"


def _signed_payload(payload: dict[str, Any]) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


def _make_subscription(
    registered_user: dict[str, Any],
    *,
    fincode_subscription_id: str,
    status: SubscriptionStatus,
    current_period_end: datetime | None = None,
    cancelled_at: datetime | None = None,
) -> Subscription:
    return Subscription(
        user_id=registered_user["user"]["id"],
        fincode_subscription_id=fincode_subscription_id,
        nonce=f"nonce-{fincode_subscription_id}",
        fincode_plan_id="plan_test_pro",
        plan_name="Pro",
        plan_amount=500,
        plan_interval="month",
        status=status,
        current_period_end=current_period_end,
        cancelled_at=cancelled_at,
    )


async def _handle(db_session, payload: dict[str, Any]) -> None:
    body, signature = _signed_payload(payload)
    await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
        payload=body, signature=signature, db=db_session
    )


async def test_payment_failed_with_uppercase_status_sets_unpaid(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    # fincode の生 status は "CAPTURED" / "CANCELED" のような独自の大文字文字列。
    # 成否判定はイベント名を正とし、生値は fincode_response にのみ残す。
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_failed_upper",
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add(sub)
    await db_session.commit()

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_failed_upper",
            "event": "subscription.payment.failed",
            "data": {
                "subscription_id": "sub_pay_failed_upper",
                "payment_id": "pay_failed_upper",
                "amount": "500",
                "status": "CANCELED",
            },
        },
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.UNPAID

    result = await db_session.scalar(
        select(SubscriptionResult).where(
            SubscriptionResult.fincode_payment_id == "pay_failed_upper"
        )
    )
    assert result is not None
    assert result.status == PaymentStatus.FAILED
    assert result.fincode_response["status"] == "CANCELED"


async def test_payment_succeeded_recovers_unpaid_to_active(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_recover",
        status=SubscriptionStatus.UNPAID,
        current_period_end=datetime(2020, 1, 1, tzinfo=UTC),
    )
    db_session.add(sub)
    await db_session.commit()

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_recover",
            "event": "subscription.payment.succeeded",
            "data": {
                "subscription_id": "sub_pay_recover",
                "payment_id": "pay_recover",
                "amount": "500",
                "status": "CAPTURED",
                "next_charge_date": "2099/01/01 00:00:00.000",
            },
        },
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.ACTIVE
    # next_charge_date（JST）で期限が延長される。
    assert sub.current_period_end is not None
    assert as_utc(sub.current_period_end) > datetime(2020, 1, 1, tzinfo=UTC)

    result = await db_session.scalar(
        select(SubscriptionResult).where(SubscriptionResult.fincode_payment_id == "pay_recover")
    )
    assert result is not None
    assert result.status == PaymentStatus.SUCCEEDED


async def test_payment_succeeded_does_not_shrink_period(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    future = datetime(2099, 1, 1, tzinfo=UTC)
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_noshrink",
        status=SubscriptionStatus.ACTIVE,
        current_period_end=future,
    )
    db_session.add(sub)
    await db_session.commit()

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_noshrink",
            "event": "subscription.payment.succeeded",
            "data": {
                "subscription_id": "sub_pay_noshrink",
                "payment_id": "pay_noshrink",
                "amount": "500",
                "status": "CAPTURED",
                "next_charge_date": "2020/01/01 00:00:00.000",
            },
        },
    )

    await db_session.refresh(sub)
    assert sub.current_period_end is not None
    assert as_utc(sub.current_period_end) == future


async def test_payment_succeeded_does_not_resurrect_cancelled(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_cancelled_ok",
        status=SubscriptionStatus.CANCELLED,
        cancelled_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    db_session.add(sub)
    await db_session.commit()

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_cancelled_ok",
            "event": "subscription.payment.succeeded",
            "data": {
                "subscription_id": "sub_pay_cancelled_ok",
                "payment_id": "pay_cancelled_ok",
                "amount": "500",
                "status": "CAPTURED",
            },
        },
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.CANCELLED


async def test_payment_failed_keeps_cancelled_subscription(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    # 解約済み契約への遅延 failed で CANCELLED を UNPAID に上書きしない
    # （partial unique index との衝突 → 再配信ループの予防）。結果行は記録される。
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_cancelled_ng",
        status=SubscriptionStatus.CANCELLED,
        cancelled_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    db_session.add(sub)
    await db_session.commit()

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_cancelled_ng",
            "event": "subscription.payment.failed",
            "data": {
                "subscription_id": "sub_pay_cancelled_ng",
                "payment_id": "pay_cancelled_ng",
                "amount": "500",
                "status": "CANCELED",
            },
        },
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.CANCELLED

    result = await db_session.scalar(
        select(SubscriptionResult).where(
            SubscriptionResult.fincode_payment_id == "pay_cancelled_ng"
        )
    )
    assert result is not None
    assert result.status == PaymentStatus.FAILED


async def test_payment_charged_at_parses_fincode_slash_format(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    # fincode の日時はスラッシュ区切り（JST）。ISO しか解析できないと受信時刻に
    # フォールバックし、charged_at が課金処理日時でなくなる。JST 09:00 = UTC 00:00。
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_charged_at",
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add(sub)
    await db_session.commit()

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_charged_at",
            "event": "subscription.payment.succeeded",
            "data": {
                "subscription_id": "sub_pay_charged_at",
                "payment_id": "pay_charged_at",
                "amount": "500",
                "status": "CAPTURED",
                "process_date": "2026/07/01 09:00:00.000",
            },
        },
    )

    result = await db_session.scalar(
        select(SubscriptionResult).where(SubscriptionResult.fincode_payment_id == "pay_charged_at")
    )
    assert result is not None
    assert as_utc(result.charged_at) == datetime(2026, 7, 1, 0, 0, tzinfo=UTC)


async def test_invalid_json_payload_raises_unprocessable(db_session) -> None:
    # 署名済みでも本文が JSON でなければ 500 でなく 422（恒久エラー、再送で直らない）。
    body = b"{not-json"
    signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    with pytest.raises(UnprocessableError):
        await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
            payload=body, signature=signature, db=db_session
        )


async def test_payment_webhook_upsert_is_idempotent(
    db_session,
    registered_user: dict[str, Any],
) -> None:
    # 同一 (fincode_subscription_id, fincode_payment_id) の再送は event_id が違っても
    # 結果行を増やさず更新する（二段冪等の upsert 側）。
    sub = _make_subscription(
        registered_user,
        fincode_subscription_id="sub_pay_idem",
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add(sub)
    await db_session.commit()

    base_data = {
        "subscription_id": "sub_pay_idem",
        "payment_id": "pay_idem",
        "amount": "500",
        "status": "FAILED",
    }
    await _handle(
        db_session,
        {"event_id": "evt_pay_idem_1", "event": "subscription.payment.failed", "data": base_data},
    )
    await _handle(
        db_session,
        {
            "event_id": "evt_pay_idem_2",
            "event": "subscription.payment.succeeded",
            "data": {**base_data, "status": "CAPTURED"},
        },
    )

    rows = list(
        (
            await db_session.execute(
                select(SubscriptionResult).where(
                    SubscriptionResult.fincode_payment_id == "pay_idem"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == PaymentStatus.SUCCEEDED

    await db_session.refresh(sub)
    # failed → UNPAID の後、同一 payment の succeeded 再送で ACTIVE に復帰する。
    assert sub.status == SubscriptionStatus.ACTIVE
