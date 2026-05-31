"""fincode Webhook レシーバー。

署名を検証し、ペイロードを解析し、``fincode_event_id`` で重複排除し、
``(fincode_subscription_id, fincode_payment_id)`` をキーに ``subscription_results``
を upsert する。不明なイベントタイプは ``dlq_reason`` に保存し、オペレーターが
イベントを失うことなく調査できるようにする。

ルーターは Webhook 配信ごとに 1 トランザクションを使用する。ハンドラーが
例外を発生させると行はロールバックされ、fincode が再配信する。
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PaymentStatus, SubscriptionStatus
from app.core.exceptions import UnauthenticatedError
from app.core.logging import get_logger
from app.models.subscription import Subscription
from app.models.subscription_result import SubscriptionResult
from app.models.webhook_event_seen import WebhookEventSeen
from app.services.audit_logger import AuditLogger

logger = get_logger(__name__)


def verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _parse_charged_at(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class FincodeWebhookHandler:
    def __init__(self, secret: str, audit: AuditLogger | None = None) -> None:
        self._secret = secret
        self._audit = audit or AuditLogger()

    async def handle(self, *, payload: bytes, signature: str | None, db: AsyncSession) -> None:
        if not verify_signature(payload, signature, self._secret):
            raise UnauthenticatedError(code="invalid_webhook_signature")

        body = json.loads(payload.decode() or "{}")
        event_id = body.get("event_id") or body.get("id") or ""
        event_type = body.get("event") or body.get("type") or "unknown"

        if not event_id:
            raise UnauthenticatedError("Missing event_id in webhook payload.", code="invalid_webhook_signature")

        # webhook_events_seen への INSERT で重複排除する。UNIQUE 制約違反が発生した場合、
        # そのイベントは既に処理済みのため変更なしで 204 ACK を返す。
        seen = WebhookEventSeen(fincode_event_id=event_id, event_type=event_type)
        db.add(seen)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return

        if event_type in {
            "payment.succeeded",
            "payment.failed",
            "subscription.payment.succeeded",
            "subscription.payment.failed",
        }:
            await self._handle_payment(body, db, seen)
        elif event_type in {"subscription.canceled", "subscription.cancelled"}:
            await self._handle_cancellation(body, db)
        else:
            seen.dlq_reason = f"unknown event_type: {event_type}"

        await db.commit()

    async def _handle_payment(self, body: dict, db: AsyncSession, seen: WebhookEventSeen) -> None:
        data = body.get("data", body)
        fincode_sub_id = data.get("subscription_id") or data.get("fincode_subscription_id")
        fincode_payment_id = data.get("payment_id") or data.get("id")
        if not fincode_sub_id or not fincode_payment_id:
            seen.dlq_reason = "missing subscription_id or payment_id"
            return

        sub = await db.scalar(
            select(Subscription).where(Subscription.fincode_subscription_id == fincode_sub_id)
        )
        if sub is None:
            seen.dlq_reason = f"no local subscription for {fincode_sub_id}"
            return

        amount_raw = data.get("amount", 0)
        try:
            amount = int(amount_raw)
        except (TypeError, ValueError):
            amount = 0

        status_value = data.get("status") or (
            PaymentStatus.SUCCEEDED
            if "succeeded" in (body.get("event") or "")
            else PaymentStatus.FAILED
        )
        charged_at = _parse_charged_at(data.get("charged_at") or data.get("process_date"))

        stmt = (
            pg_insert(SubscriptionResult)
            .values(
                subscription_id=sub.id,
                fincode_subscription_id=fincode_sub_id,
                fincode_payment_id=fincode_payment_id,
                status=status_value,
                amount=amount,
                charged_at=charged_at,
                fincode_response=data,
            )
            .on_conflict_do_update(
                constraint="uq_subscription_results_sub_payment",
                set_={
                    "status": status_value,
                    "amount": amount,
                    "charged_at": charged_at,
                    "fincode_response": data,
                },
            )
        )
        await db.execute(stmt)

        if status_value in {PaymentStatus.FAILED, SubscriptionStatus.UNPAID}:
            sub.status = SubscriptionStatus.UNPAID

        await self._audit.record(
            db,
            user_id=sub.user_id,
            event=f"webhook.{body.get('event') or 'payment'}",
            auditable_type="subscription_result",
            auditable_id=sub.id,
            after={"status": status_value, "amount": amount},
        )

    async def _handle_cancellation(self, body: dict, db: AsyncSession) -> None:
        data = body.get("data", body)
        fincode_sub_id = data.get("subscription_id") or data.get("id")
        if not fincode_sub_id:
            return
        sub = await db.scalar(
            select(Subscription).where(Subscription.fincode_subscription_id == fincode_sub_id)
        )
        if sub is None:
            return
        if sub.status != SubscriptionStatus.CANCELLED:
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancelled_at = datetime.now(timezone.utc)
        await self._audit.record(
            db,
            user_id=sub.user_id,
            event="webhook.subscription_cancelled",
            auditable_type="subscription",
            auditable_id=sub.id,
            after={"status": SubscriptionStatus.CANCELLED},
        )
