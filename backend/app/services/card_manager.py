"""カード登録・一覧・削除のオーケストレーション。

信頼境界: このサービスは fincode ラッパーとローカル DB を一つの ``AsyncSession``
内で組み合わせる。監査ログ行は同じセッション内に書き込まれるため、ビジネス状態と
監査証跡が一緒にコミットされる。ルーターがマネージャーの返却後に ``await db.commit()``
を呼び出す — マネージャー自身はコミットしないため、より大きなフローに組み込める。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.fincode_card import FincodeCard
from app.models.fincode_customer import FincodeCustomer
from app.models.subscription import Subscription
from app.models.user import User
from app.services.audit_logger import AuditLogger
from app.services.base_manager import BaseManager
from app.services.fincode.card_service import FincodeCardService
from app.services.fincode.client import FincodeClient
from app.services.subscription_periods import usable_subscription_conditions


def _parse_expire(expire: str | None) -> tuple[int, int]:
    """fincode は expire を YYMM 形式で返す。(month, full_year) のタプルを返す。"""

    if not expire or len(expire) < 4:
        return 1, 1970
    try:
        year = int(expire[:2]) + 2000
        month = int(expire[2:4])
        return month, year
    except ValueError:
        return 1, 1970


class CardManager(BaseManager):
    def __init__(self, client: FincodeClient, audit: AuditLogger | None = None) -> None:
        super().__init__(client, audit)
        self._card_service = FincodeCardService(client)

    @property
    def auditable_type(self) -> str:
        return "fincode_card"

    async def list_cards(self, db: AsyncSession, user: User) -> list[FincodeCard]:
        stmt = (
            select(FincodeCard)
            .where(FincodeCard.user_id == user.id, FincodeCard.deleted_at.is_(None))
            .order_by(FincodeCard.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def register_card(self, db: AsyncSession, user: User, token: str) -> FincodeCard:
        customer = await self._customers.ensure(db, user)
        existing_count = await db.scalar(
            select(func.count())
            .select_from(FincodeCard)
            .where(FincodeCard.user_id == user.id, FincodeCard.deleted_at.is_(None))
        )
        default_flag = "1" if not existing_count else "0"
        raw = await self._card_service.create(
            user_id=user.id,
            customer_id=customer.fincode_customer_id,
            token=token,
            default_flag=default_flag,
        )
        month, year = _parse_expire(raw.get("expire"))
        card = FincodeCard(
            user_id=user.id,
            fincode_customer_id=customer.id,
            fincode_card_id=raw.get("id") or f"card_local_{user.id}",
            brand=raw.get("brand") or raw.get("card_brand") or "UNKNOWN",
            last4=(raw.get("card_no") or raw.get("last4") or "0000")[-4:],
            exp_month=month,
            exp_year=year,
        )
        db.add(card)
        await db.flush()
        await self._audit.record(
            db,
            user_id=user.id,
            event="card.create",
            auditable_type=self.auditable_type,
            auditable_id=card.id,
            after={"brand": card.brand, "last4": card.last4},
        )
        return card

    async def delete_card(self, db: AsyncSession, user: User, card_id: int) -> None:
        card = await db.get(FincodeCard, card_id)
        if card is None or card.deleted_at is not None:
            raise NotFoundError(code="card_not_found")
        if card.user_id != user.id:
            raise ForbiddenError()

        active = await db.execute(
            select(Subscription).where(
                Subscription.fincode_card_id == card.id,
                *usable_subscription_conditions(datetime.now(UTC)),
            )
        )
        if active.scalars().first() is not None:
            raise ConflictError(code="card_in_use")

        customer = await db.get_one(FincodeCustomer, card.fincode_customer_id)

        await self._card_service.delete(
            customer_id=customer.fincode_customer_id,
            card_id=card.fincode_card_id,
        )
        card.deleted_at = datetime.now(UTC)
        await db.flush()
        await self._audit.record(
            db,
            user_id=user.id,
            event="card.delete",
            auditable_type=self.auditable_type,
            auditable_id=card.id,
            before={"brand": card.brand, "last4": card.last4},
            after={"deleted_at": card.deleted_at.isoformat()},
        )
