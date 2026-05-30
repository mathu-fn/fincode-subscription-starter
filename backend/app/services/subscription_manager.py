"""契約オーケストレーション。

1ユーザー1アクティブ契約の不変条件は、partial unique index
（``WHERE status = 'active'``）によって DB 層で強制される。これにより同時リクエストが
両方とも成功することはない。このサービスは一般ケースがインデックスをヒットしないよう
``ActiveSubscriptionExistsError`` を最初の協調的なガードとして発生させるが、
インデックスこそがガードをレースセーフにしている。

キャンセルは同期的: ローカル行の ``status`` を即座に ``'cancelled'`` に反転させる。
``current_period_end`` と最終的な ``subscription_results`` 行は、fincode が
Webhook を配信した後に埋まる。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionStatus
from app.core.exceptions import (
    ActiveSubscriptionExistsError,
    ExpiredCardError,
    OwnershipError,
    SubscriptionNotFoundError,
)
from app.models.fincode_card import FincodeCard
from app.models.subscription import Subscription
from app.models.subscription_result import SubscriptionResult
from app.models.user import User
from app.services.audit_logger import AuditLogger
from app.services.customer_sync_service import CustomerSyncService
from app.services.fincode.client import FincodeClient
from app.services.fincode.idempotency import new_nonce
from app.services.fincode.plan_service import FincodePlanService, PlanData
from app.services.fincode.subscription_service import FincodeSubscriptionService


class SubscriptionManager:
    def __init__(self, client: FincodeClient, audit: AuditLogger | None = None) -> None:
        self._client = client
        self._customers = CustomerSyncService(client)
        self._plans = FincodePlanService(client)
        self._subs = FincodeSubscriptionService(client)
        self._audit = audit or AuditLogger()

    async def get_active(self, db: AsyncSession, user: User) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.ACTIVE
            )
            .order_by(desc(Subscription.created_at))
            .limit(1)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_plans(self) -> list[PlanData]:
        return await self._plans.list_active()

    async def subscribe(
        self,
        db: AsyncSession,
        user: User,
        *,
        plan_id: str,
        card_id: int,
        idempotency_key: str | None = None,
    ) -> Subscription:
        # Idempotency-Key リプレイ: 同じクライアント提供キーによるリトライは、
        # 新しい fincode 契約を開始する代わりに以前の成功した行を返す。
        # これがなければ、レスポンスが途中で失われた後のクライアントリトライが
        # 新しいノンスで fincode に到達し、新しい Idempotency-Key で重複契約
        # （二重請求）を作成してしまう。
        if idempotency_key is not None:
            prior = await db.scalar(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.nonce == idempotency_key,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
            if prior is not None:
                return prior

        existing = await self.get_active(db, user)
        if existing is not None:
            raise ActiveSubscriptionExistsError()

        plan = await self._plans.fetch(plan_id)

        # このユーザーのカードであり、削除・期限切れでないことを確認する。
        card = await db.get(FincodeCard, card_id)
        if card is None or card.deleted_at is not None:
            raise SubscriptionNotFoundError("Card not found.")
        if card.user_id != user.id:
            raise OwnershipError()

        now = datetime.now(timezone.utc)
        # exp_year は 4 桁で保存される。exp の日付が現在より前なら期限切れ。
        if (card.exp_year, card.exp_month) < (now.year, now.month):
            raise ExpiredCardError()

        customer = await self._customers.ensure(db, user)

        # クライアントの Idempotency-Key をノンスとして再利用することで、
        # クライアントリトライ全体で決定論的な fincode Idempotency-Key が安定する
        # （app/services/fincode/idempotency.py の ``idem_key`` を参照）。
        nonce = idempotency_key or new_nonce()
        # ローカル行を先挿入してレース時に partial unique index が発火できるようにする。
        sub = Subscription(
            user_id=user.id,
            fincode_customer_id=customer.id,
            fincode_card_id=card.id,
            fincode_subscription_id=None,
            nonce=nonce,
            fincode_plan_id=plan["fincode_plan_id"],
            plan_name=plan["name"],
            plan_amount=plan["amount"],
            plan_interval=plan["interval"],
            plan_snapshot=plan["raw"],
            status=SubscriptionStatus.ACTIVE,
        )
        db.add(sub)
        try:
            await db.flush()
        except IntegrityError as e:
            await db.rollback()
            raise ActiveSubscriptionExistsError() from e

        try:
            raw = await self._subs.create(
                user_id=user.id,
                customer_id=customer.fincode_customer_id,
                card_id=card.fincode_card_id,
                plan_id=plan["fincode_plan_id"],
                nonce=nonce,
            )
        except Exception:
            await db.delete(sub)
            await db.flush()
            raise

        sub.fincode_subscription_id = raw.get("id")
        if raw.get("current_period_end"):
            try:
                sub.current_period_end = datetime.fromisoformat(raw["current_period_end"])
            except (TypeError, ValueError):
                pass
        await db.flush()

        await self._audit.record(
            db,
            user_id=user.id,
            event="subscription.create",
            auditable_type="subscription",
            auditable_id=sub.id,
            after={
                "fincode_subscription_id": sub.fincode_subscription_id,
                "plan_name": sub.plan_name,
                "plan_amount": sub.plan_amount,
            },
        )
        return sub

    async def cancel(self, db: AsyncSession, user: User) -> Subscription:
        sub = await self.get_active(db, user)
        if sub is None:
            raise SubscriptionNotFoundError()
        if sub.fincode_subscription_id is None:
            # ローカルのみの行; ステータスを反転するだけ。
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancelled_at = datetime.now(timezone.utc)
            await db.flush()
            return sub

        await self._subs.cancel(fincode_subscription_id=sub.fincode_subscription_id)
        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = datetime.now(timezone.utc)
        await db.flush()

        await self._audit.record(
            db,
            user_id=user.id,
            event="subscription.cancel",
            auditable_type="subscription",
            auditable_id=sub.id,
            before={"status": SubscriptionStatus.ACTIVE},
            after={
                "status": SubscriptionStatus.CANCELLED,
                "cancelled_at": sub.cancelled_at.isoformat(),
            },
        )
        return sub

    async def list_history(
        self, db: AsyncSession, user: User, *, page: int, per_page: int
    ) -> tuple[list[SubscriptionResult], int]:
        if page < 1:
            page = 1
        per_page = max(1, min(per_page, 100))
        offset = (page - 1) * per_page

        sub_ids_stmt = select(Subscription.id).where(Subscription.user_id == user.id)
        sub_ids = [row[0] for row in (await db.execute(sub_ids_stmt)).all()]
        if not sub_ids:
            return [], 0

        total = (
            await db.scalar(
                select(func.count())
                .select_from(SubscriptionResult)
                .where(SubscriptionResult.subscription_id.in_(sub_ids))
            )
        ) or 0

        rows_stmt = (
            select(SubscriptionResult)
            .where(SubscriptionResult.subscription_id.in_(sub_ids))
            .order_by(desc(SubscriptionResult.charged_at))
            .limit(per_page)
            .offset(offset)
        )
        rows = list((await db.execute(rows_stmt)).scalars().all())
        return rows, total
