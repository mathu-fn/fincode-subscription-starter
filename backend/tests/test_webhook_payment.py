from __future__ import annotations

import hashlib
import hmac
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
from tests.conftest import WEBHOOK_SECRET, signed_payload


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
    body, signature = signed_payload(payload)
    await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
        payload=body, signature=signature, db=db_session
    )


async def test_payment_failed_with_uppercase_status_sets_unpaid(
    db_session,
    subscribed_user: dict[str, Any],
) -> None:
    # fincode の生 status は "CAPTURED" / "CANCELED" のような独自の大文字文字列。
    # 成否判定はイベント名を正とし、生値は fincode_response にのみ残す。
    sub = subscribed_user["subscription"]

    await _handle(
        db_session,
        {
            "event_id": "evt_pay_failed_upper",
            "event": "subscription.payment.failed",
            "data": {
                "subscription_id": sub.fincode_subscription_id,
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


async def test_duplicate_event_id_is_ignored(
    db_session,
    subscribed_user: dict[str, Any],
) -> None:
    # 二段冪等の第 1 段: 同一 event_id の再送は webhook_events_seen の UNIQUE 違反で
    # 検知し、業務処理へ入らず ACK する。状態遷移も結果行も二重適用されない。
    sub = subscribed_user["subscription"]

    payload = {
        "event_id": "evt_dedup_1",
        "event": "subscription.payment.failed",
        "data": {
            "subscription_id": sub.fincode_subscription_id,
            "payment_id": "pay_dedup",
            "amount": "500",
            "status": "CANCELED",
        },
    }
    await _handle(db_session, payload)
    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.UNPAID

    # 手動で ACTIVE へ戻してから同一 event_id を再送。処理済みイベントなので
    # 再度 UNPAID に落とされない（第 2 段の upsert とは独立に第 1 段で止まる）。
    sub.status = SubscriptionStatus.ACTIVE
    await db_session.commit()

    await _handle(db_session, payload)
    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.ACTIVE

    rows = list(
        (
            await db_session.execute(
                select(SubscriptionResult).where(
                    SubscriptionResult.fincode_payment_id == "pay_dedup"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_missing_event_id_is_unprocessable_not_unauthorized(db_session) -> None:
    # 署名は正しいが event_id が無いペイロード。重複排除キーが無く安全に処理できない
    # ため 422 (invalid_webhook_payload) で fincode に差し戻す。署名不正 (401) とは区別する。
    body, signature = signed_payload({"event": "subscription.payment.succeeded", "data": {}})
    with pytest.raises(UnprocessableError) as exc_info:
        await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
            payload=body, signature=signature, db=db_session
        )
    assert exc_info.value.code == "invalid_webhook_payload"


async def test_invalid_json_payload_raises_unprocessable(db_session) -> None:
    # 署名済みでも本文が JSON でなければ 500 でなく 422（恒久エラー、再送で直らない）。
    body = b"{not-json"
    signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    with pytest.raises(UnprocessableError) as exc_info:
        await FincodeWebhookHandler(WEBHOOK_SECRET).handle(
            payload=body, signature=signature, db=db_session
        )
    assert exc_info.value.code == "invalid_webhook_payload"


async def test_charged_at_parsed_from_fincode_process_date(
    db_session,
    subscribed_user: dict[str, Any],
) -> None:
    # fincode の process_date はスラッシュ区切りの JST。受信時刻ではなく
    # 実課金日時が UTC に変換されて保存される（履歴 API のソートキー）。
    sub = subscribed_user["subscription"]

    await _handle(
        db_session,
        {
            "event_id": "evt_charged_at",
            "event": "subscription.payment.succeeded",
            "data": {
                "subscription_id": sub.fincode_subscription_id,
                "payment_id": "pay_charged_at",
                "amount": "500",
                "status": "CAPTURED",
                "process_date": "2026/07/08 12:00:00.000",
            },
        },
    )

    result = await db_session.scalar(
        select(SubscriptionResult).where(SubscriptionResult.fincode_payment_id == "pay_charged_at")
    )
    assert result is not None
    # JST 12:00 = UTC 03:00
    assert as_utc(result.charged_at) == datetime(2026, 7, 8, 3, 0, tzinfo=UTC)


async def test_payment_webhook_upsert_is_idempotent(
    db_session,
    subscribed_user: dict[str, Any],
) -> None:
    # 同一 (fincode_subscription_id, fincode_payment_id) の再送は event_id が違っても
    # 結果行を増やさず更新する（二段冪等の upsert 側）。
    sub = subscribed_user["subscription"]

    base_data = {
        "subscription_id": sub.fincode_subscription_id,
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
