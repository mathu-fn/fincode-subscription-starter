"""契約オーケストレーション。

1ユーザー1契約の不変条件は、partial unique index
（``WHERE status IN ('active', 'unpaid')``）によって DB 層で強制される。unpaid を
含めるのは fincode 側のサブスクが生きたまま新規契約（二重課金）を許さないため。
これにより同時リクエストが
両方とも成功することはない。このサービスは一般ケースがインデックスをヒットしないよう
``ConflictError`` を最初の協調的なガードとして発生させるが、
インデックスこそがガードをレースセーフにしている。

有料契約のキャンセルは請求停止を即時に予約し、``current_period_end`` までは
ローカル行を ``active`` のまま保持する。期間が切れた解約予約は、次の状態変更前に
``cancelled`` へ遅延確定する。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionStatus
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableError,
)
from app.core.logging import get_logger
from app.models.fincode_card import FincodeCard
from app.models.fincode_customer import FincodeCustomer
from app.models.subscription import Subscription
from app.models.subscription_result import SubscriptionResult
from app.models.user import User
from app.services.audit_logger import AuditLogger
from app.services.base_manager import BaseManager
from app.services.fincode.client import FincodeClient
from app.services.fincode.idempotency import new_nonce
from app.services.fincode.plan_service import FincodePlanService, PlanData
from app.services.fincode.subscription_service import FincodeSubscriptionService
from app.services.subscription_periods import (
    apply_current_period_end,
    cancel_at_period_end,
    has_future_period,
    usable_subscription_conditions,
)

logger = get_logger(__name__)

# 0円フリープランはアプリ側で合成する番兵プラン。fincode には存在しない
# （fincode は 0 円プランを作成できない）。fincode のプランIDは生成トークン
# （``plan_test_*`` 等）なので ``"free"`` と衝突しない。契約・解約は fincode を
# 介さず完全にローカルで完結する。
FREE_PLAN_ID = "free"
FREE_PLAN: PlanData = {
    "fincode_plan_id": FREE_PLAN_ID,
    "name": "フリープラン",
    "amount": 0,
    "currency": "JPY",
    "interval": "month",
    "raw": {
        "id": FREE_PLAN_ID,
        "plan_name": "フリープラン",
        "amount": "0",
        "synthetic": True,
    },
}


def _apply_plan_snapshot(sub: Subscription, plan: PlanData) -> None:
    sub.fincode_plan_id = plan["fincode_plan_id"]
    sub.plan_name = plan["name"]
    sub.plan_amount = plan["amount"]
    sub.plan_interval = plan["interval"]
    sub.plan_snapshot = plan["raw"]


class SubscriptionManager(BaseManager):
    def __init__(self, client: FincodeClient, audit: AuditLogger | None = None) -> None:
        super().__init__(client, audit)
        self._plans = FincodePlanService(client)
        self._subs = FincodeSubscriptionService(client)

    @property
    def auditable_type(self) -> str:
        return "subscription"

    async def get_active(self, db: AsyncSession, user: User) -> Subscription | None:
        now = datetime.now(UTC)
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user.id,
                *usable_subscription_conditions(now),
            )
            .order_by(desc(Subscription.created_at))
            .limit(1)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def _finalize_elapsed_cancellations(self, db: AsyncSession, user: User) -> None:
        now = datetime.now(UTC)
        stmt = select(Subscription).where(
            Subscription.user_id == user.id,
            # unpaid も対象に含める。解約予約中に未払いへ落ちた契約を期間満了で
            # cancelled に確定させないと、get_active には見えないのに partial unique
            # index には引っかかる行が残り、新規契約を永久にブロックしてしまう。
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.UNPAID]),
            Subscription.cancelled_at.is_not(None),
            or_(Subscription.current_period_end.is_(None), Subscription.current_period_end <= now),
        )
        rows = list((await db.execute(stmt)).scalars().all())
        for sub in rows:
            sub.status = SubscriptionStatus.CANCELLED
        if rows:
            await db.flush()

    async def list_plans(self) -> list[PlanData]:
        return [FREE_PLAN, *await self._plans.list_active()]

    async def _get_usable_card(
        self,
        db: AsyncSession,
        user: User,
        card_id: int,
    ) -> FincodeCard:
        card = await db.get(FincodeCard, card_id)
        # 他ユーザーのカードも「存在しない」扱いに統一する。403 を返すと連番 ID に
        # 対してカードの存在有無を露呈してしまう（ID 列挙対策）。
        if card is None or card.deleted_at is not None or card.user_id != user.id:
            raise NotFoundError("Card not found.", code="card_not_found")

        now = datetime.now(UTC)
        # exp_year は 4 桁で保存される。
        if (card.exp_year, card.exp_month) < (now.year, now.month):
            raise UnprocessableError(code="expired_card")
        return card

    async def subscribe(
        self,
        db: AsyncSession,
        user: User,
        *,
        plan_id: str,
        card_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> Subscription:
        await self._finalize_elapsed_cancellations(db, user)

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
                    *usable_subscription_conditions(datetime.now(UTC)),
                )
            )
            if prior is not None:
                return prior

        existing = await self.get_active(db, user)
        if existing is not None:
            raise ConflictError(code="active_subscription_exists")

        is_free = plan_id == FREE_PLAN_ID

        card: FincodeCard | None = None
        customer: FincodeCustomer | None = None
        if is_free:
            plan = FREE_PLAN
        else:
            plan = await self._plans.fetch(plan_id)
            if card_id is None:
                raise UnprocessableError(code="card_required")
            card = await self._get_usable_card(db, user, card_id)
            customer = await self._customers.ensure(db, user)

        # クライアントの Idempotency-Key をノンスとして再利用することで、
        # クライアントリトライ全体で決定論的な fincode Idempotency-Key が安定する
        # （app/services/fincode/idempotency.py の ``idem_key`` を参照）。
        nonce = idempotency_key or new_nonce()
        # ローカル行を先挿入してレース時に partial unique index が発火できるようにする。
        sub = Subscription(
            user_id=user.id,
            fincode_customer_id=customer.id if customer is not None else None,
            fincode_card_id=card.id if card is not None else None,
            fincode_subscription_id=None,
            nonce=nonce,
            status=SubscriptionStatus.ACTIVE,
        )
        _apply_plan_snapshot(sub, plan)
        db.add(sub)
        try:
            await db.flush()
        except IntegrityError as e:
            await db.rollback()
            raise ConflictError(code="active_subscription_exists") from e

        if not is_free:
            assert card is not None and customer is not None
            # fincode 契約作成が失敗した場合、例外はルーターの commit 前に伝播し、
            # get_session の rollback が未コミットの先挿入行ごと破棄する（補償削除は不要）。
            raw = await self._subs.create(
                user_id=user.id,
                customer_id=customer.fincode_customer_id,
                card_id=card.fincode_card_id,
                plan_id=plan["fincode_plan_id"],
                nonce=nonce,
            )
            sub.fincode_subscription_id = raw.get("id")
            apply_current_period_end(sub, raw)
            await db.flush()

        await self._audit.record(
            db,
            user_id=user.id,
            event="subscription.create",
            auditable_type=self.auditable_type,
            auditable_id=sub.id,
            after={
                "fincode_subscription_id": sub.fincode_subscription_id,
                "plan_name": sub.plan_name,
                "plan_amount": sub.plan_amount,
            },
        )
        return sub

    async def change_plan(
        self,
        db: AsyncSession,
        user: User,
        *,
        plan_id: str,
        card_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> Subscription:
        await self._finalize_elapsed_cancellations(db, user)
        sub = await self.get_active(db, user)
        if sub is None:
            raise NotFoundError(code="subscription_not_found")
        if cancel_at_period_end(sub):
            raise ConflictError(code="subscription_cancel_scheduled")
        if sub.fincode_plan_id == plan_id:
            return sub

        before = {
            "fincode_subscription_id": sub.fincode_subscription_id,
            "fincode_plan_id": sub.fincode_plan_id,
            "plan_name": sub.plan_name,
            "plan_amount": sub.plan_amount,
            "plan_interval": sub.plan_interval,
        }

        if plan_id == FREE_PLAN_ID:
            if sub.fincode_subscription_id is not None:
                await self._subs.cancel(fincode_subscription_id=sub.fincode_subscription_id)
            _apply_plan_snapshot(sub, FREE_PLAN)
            sub.fincode_customer_id = None
            sub.fincode_card_id = None
            sub.fincode_subscription_id = None
            sub.current_period_end = None
            sub.cancelled_at = None
            sub.status = SubscriptionStatus.ACTIVE
            await db.flush()
        else:
            plan = await self._plans.fetch(plan_id)
            nonce = idempotency_key or new_nonce()
            if sub.fincode_subscription_id is None:
                if card_id is None:
                    raise UnprocessableError(code="card_required")
                card = await self._get_usable_card(db, user, card_id)
                customer = await self._customers.ensure(db, user)
                raw = await self._subs.create(
                    user_id=user.id,
                    customer_id=customer.fincode_customer_id,
                    card_id=card.fincode_card_id,
                    plan_id=plan["fincode_plan_id"],
                    nonce=nonce,
                )
                sub.fincode_customer_id = customer.id
                sub.fincode_card_id = card.id
                sub.fincode_subscription_id = raw.get("id")
                apply_current_period_end(sub, raw)
            else:
                # fincode は課金開始済みサブスクのプラン変更（PUT /v1/subscriptions/{id}）を
                # 拒否する（ESC03194031「既に課金処理が開始されてます。対象のサブスクリプション
                # は変更できません」）。そのため有料→有料の変更は、現行 fincode サブスクを解約し、
                # 新プランで作り直して同じローカル ``subscriptions`` 行を更新する。fincode に日割りは
                # 無く、新サブスクは新しい請求サイクルで開始される（apply_current_period_end は
                # 新サブスクの期限で置き換える。only_extend は使わない）。
                #
                # 注意（非アトミック）: 解約と再作成は別 API 呼び出しでトランザクションにまとめられない。
                # 解約成功後に再作成が失敗すると、fincode 上はサブスク無し・ローカル行は変更前へ
                # ロールバックされ不整合になる。失敗はコンテキスト付きでログに残す。本番では補償
                # （再試行・手動復旧導線）が必要。
                card_id_for_change = card_id if card_id is not None else sub.fincode_card_id
                if card_id_for_change is None:
                    raise UnprocessableError(code="card_required")
                card = await self._get_usable_card(db, user, card_id_for_change)
                customer = await self._customers.ensure(db, user)
                old_fincode_subscription_id = sub.fincode_subscription_id
                await self._subs.cancel(fincode_subscription_id=old_fincode_subscription_id)
                try:
                    raw = await self._subs.create(
                        user_id=user.id,
                        customer_id=customer.fincode_customer_id,
                        card_id=card.fincode_card_id,
                        plan_id=plan["fincode_plan_id"],
                        nonce=nonce,
                    )
                except Exception:
                    # 解約は済んでいるが再作成に失敗。ローカル行はロールバックされ
                    # fincode と不整合になる危険な状態。補償のため孤立した解約済み ID を残す。
                    logger.error(
                        "plan_change_recreate_failed",
                        user_id=user.id,
                        cancelled_fincode_subscription_id=old_fincode_subscription_id,
                        target_plan_id=plan["fincode_plan_id"],
                    )
                    raise
                sub.fincode_customer_id = customer.id
                sub.fincode_card_id = card.id
                sub.fincode_subscription_id = raw.get("id")
                apply_current_period_end(sub, raw)
            _apply_plan_snapshot(sub, plan)
            sub.cancelled_at = None
            sub.status = SubscriptionStatus.ACTIVE
            await db.flush()

        await self._audit.record(
            db,
            user_id=user.id,
            event="subscription.change_plan",
            auditable_type=self.auditable_type,
            auditable_id=sub.id,
            before=before,
            after={
                "fincode_subscription_id": sub.fincode_subscription_id,
                "fincode_plan_id": sub.fincode_plan_id,
                "plan_name": sub.plan_name,
                "plan_amount": sub.plan_amount,
                "plan_interval": sub.plan_interval,
            },
        )
        return sub

    async def cancel(self, db: AsyncSession, user: User) -> Subscription:
        await self._finalize_elapsed_cancellations(db, user)
        sub = await self.get_active(db, user)
        if sub is None:
            raise NotFoundError(code="subscription_not_found")
        if cancel_at_period_end(sub):
            return sub
        if sub.fincode_subscription_id is None:
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancelled_at = datetime.now(UTC)
            await db.flush()
            return sub

        before = {
            "status": sub.status,
            "cancel_at_period_end": False,
        }
        raw = await self._subs.cancel(fincode_subscription_id=sub.fincode_subscription_id)
        apply_current_period_end(sub, raw, only_extend=True)
        sub.cancelled_at = datetime.now(UTC)
        if has_future_period(sub):
            sub.status = SubscriptionStatus.ACTIVE
        else:
            sub.status = SubscriptionStatus.CANCELLED
        await db.flush()

        await self._audit.record(
            db,
            user_id=user.id,
            event="subscription.cancel",
            auditable_type=self.auditable_type,
            auditable_id=sub.id,
            before=before,
            after={
                "status": sub.status,
                "cancel_at_period_end": cancel_at_period_end(sub),
                "cancelled_at": sub.cancelled_at.isoformat(),
                "current_period_end": (
                    sub.current_period_end.isoformat() if sub.current_period_end else None
                ),
            },
        )
        return sub

    async def list_history(
        self, db: AsyncSession, user: User, *, page: int, per_page: int
    ) -> tuple[list[SubscriptionResult], int]:
        # page / per_page の範囲はルーターの Query(ge=1, le=100) が保証済み。
        offset = (page - 1) * per_page

        total = (
            await db.scalar(
                select(func.count())
                .select_from(SubscriptionResult)
                .join(Subscription, SubscriptionResult.subscription_id == Subscription.id)
                .where(Subscription.user_id == user.id)
            )
        ) or 0

        rows_stmt = (
            select(SubscriptionResult)
            .join(Subscription, SubscriptionResult.subscription_id == Subscription.id)
            .where(Subscription.user_id == user.id)
            .order_by(desc(SubscriptionResult.charged_at))
            .limit(per_page)
            .offset(offset)
        )
        rows = list((await db.execute(rows_stmt)).scalars().all())
        return rows, total
