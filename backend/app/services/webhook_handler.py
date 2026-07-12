"""fincode Webhook レシーバー。

署名を検証し、ペイロードを解析し、``fincode_event_id`` で重複排除し、
``(fincode_subscription_id, fincode_payment_id)`` をキーに ``subscription_results``
を upsert する。不明なイベントタイプは ``dlq_reason`` に保存し、オペレーターが
イベントを失うことなく調査できるようにする。

ルーターは Webhook 配信ごとに 1 トランザクションを使用し、コミットも
ルーター側が行う（他の Manager と同じトランザクション所有規約）。ハンドラーが
例外を発生させると行はロールバックされ、fincode が再配信する。

fincode への HTTP 呼び出しを持たない受信専用サービスなので、fincode ラッパー層
（``app/services/fincode/``）ではなくドメインサービス層（``app/services/``）に置く。
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PaymentStatus, SubscriptionStatus
from app.core.exceptions import UnauthenticatedError, UnprocessableError
from app.core.logging import get_logger
from app.models.subscription import Subscription
from app.models.subscription_result import SubscriptionResult
from app.models.webhook_event_seen import WebhookEventSeen
from app.services.audit_logger import AuditLogger
from app.services.subscription_periods import (
    apply_current_period_end,
    cancel_at_period_end,
    has_future_period,
    parse_fincode_datetime,
)

logger = get_logger(__name__)


def verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _parse_charged_at(value: Any) -> datetime:
    # fincode の日時はスラッシュ区切り JST（"2026/07/08 12:00:00.000" 等）。ISO 形式と
    # 合わせて subscription_periods.parse_fincode_datetime に解析を一本化する。
    # 解析不能な場合のみ受信時刻へフォールバックする（charged_at は NOT NULL かつ
    # 履歴 API のソートキーのため、欠損より近似値を優先する）。
    return parse_fincode_datetime(value) or datetime.now(UTC)


class FincodeWebhookHandler:
    def __init__(self, secret: str, audit: AuditLogger | None = None) -> None:
        self._secret = secret
        self._audit = audit or AuditLogger()

    @staticmethod
    async def _find_subscription(db: AsyncSession, fincode_sub_id: str) -> Subscription | None:
        """fincode サブスク ID からローカル契約行を検索する（無ければ None）。"""
        sub: Subscription | None = await db.scalar(
            select(Subscription).where(Subscription.fincode_subscription_id == fincode_sub_id)
        )
        return sub

    async def handle(self, *, payload: bytes, signature: str | None, db: AsyncSession) -> None:
        if not verify_signature(payload, signature, self._secret):
            raise UnauthenticatedError(code="invalid_webhook_signature")

        # 署名済みでも本文が壊れている可能性はある。素の JSONDecodeError を 500 に
        # せず 422 へ翻訳する。再送されても直らない恒久エラーなので 5xx は返さない。
        try:
            body = json.loads(payload.decode() or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise UnprocessableError(code="invalid_webhook_payload") from e
        if not isinstance(body, dict):
            raise UnprocessableError(code="invalid_webhook_payload")
        event_id = body.get("event_id") or body.get("id") or ""
        event_type = body.get("event") or body.get("type") or "unknown"

        if not event_id:
            # 署名検証は通過しているため「署名不正」とは区別する。event_id は重複排除の
            # キーなので、無いイベントは安全に処理できず非 2xx で fincode に差し戻す。
            raise UnprocessableError(
                "Missing event_id in webhook payload.", code="invalid_webhook_payload"
            )

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
            await self._handle_payment(body, db, seen, event_type=event_type)
        elif event_type in {"subscription.canceled", "subscription.cancelled"}:
            await self._handle_cancellation(body, db)
        else:
            seen.dlq_reason = f"unknown event_type: {event_type}"

        # コミットはルーターが行う。ここでは保留中の変更を flush だけして、
        # 同一トランザクション内の後続処理（テスト含む）から見える状態にする。
        await db.flush()

    async def _handle_payment(
        self, body: dict[str, Any], db: AsyncSession, seen: WebhookEventSeen, *, event_type: str
    ) -> None:
        data = body.get("data", body)
        fincode_sub_id = data.get("subscription_id") or data.get("fincode_subscription_id")
        fincode_payment_id = data.get("payment_id")
        if not fincode_payment_id and "data" in body:
            # "id" へのフォールバックは data ラッパがある形状に限定する。ラッパ無しの
            # フラット形状ではトップレベルの "id" はイベント ID であり、payment_id と
            # 誤認すると upsert キーを汚染する。
            fincode_payment_id = data.get("id")
        if not fincode_sub_id or not fincode_payment_id:
            seen.dlq_reason = "missing subscription_id or payment_id"
            return

        sub = await self._find_subscription(db, fincode_sub_id)
        if sub is None:
            seen.dlq_reason = f"no local subscription for {fincode_sub_id}"
            return

        amount_raw = data.get("amount", 0)
        try:
            amount = int(amount_raw)
        except (TypeError, ValueError):
            amount = 0

        # 成否の正本はイベント名。fincode の生 ``status``（"CAPTURED" 等の独自文字列）は
        # 判定に使わず ``fincode_response`` JSONB にそのまま保存する。
        succeeded = "succeeded" in event_type
        status_value = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
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

        if succeeded:
            # 課金成功は支払い済み期限を延ばす方向にのみ作用させる（only_extend）。
            apply_current_period_end(sub, data, only_extend=True)
            if sub.status == SubscriptionStatus.UNPAID:
                sub.status = SubscriptionStatus.ACTIVE
        elif sub.status == SubscriptionStatus.ACTIVE:
            # 失敗で UNPAID にするのは ACTIVE からのみ。解約済み契約への遅延 failed で
            # CANCELLED を上書きすると partial unique index と衝突し再配信ループになる。
            sub.status = SubscriptionStatus.UNPAID

        await self._audit.record(
            db,
            user_id=sub.user_id,
            event=f"webhook.{body.get('event') or 'payment'}",
            auditable_type="subscription_result",
            auditable_id=sub.id,
            after={"status": status_value, "amount": amount},
        )

    async def _handle_cancellation(self, body: dict[str, Any], db: AsyncSession) -> None:
        data = body.get("data", body)
        fincode_sub_id = data.get("subscription_id")
        if not fincode_sub_id and "data" in body:
            # _handle_payment と同じ理由で、"id" フォールバックは data ラッパがある
            # 形状（= "id" がサブスクオブジェクトの ID である形状）に限定する。
            fincode_sub_id = data.get("id")
        if not fincode_sub_id:
            return
        sub = await self._find_subscription(db, fincode_sub_id)
        if sub is None:
            return
        apply_current_period_end(sub, data, only_extend=True)
        now = datetime.now(UTC)
        if has_future_period(sub, now):
            sub.status = SubscriptionStatus.ACTIVE
            if sub.cancelled_at is None:
                sub.cancelled_at = now
        elif sub.status != SubscriptionStatus.CANCELLED:
            sub.status = SubscriptionStatus.CANCELLED
            if sub.cancelled_at is None:
                sub.cancelled_at = now
        await self._audit.record(
            db,
            user_id=sub.user_id,
            event="webhook.subscription_cancelled",
            auditable_type="subscription",
            auditable_id=sub.id,
            after={
                "status": sub.status,
                "cancel_at_period_end": cancel_at_period_end(sub),
            },
        )
