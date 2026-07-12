from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.fincode_card import FincodeCard
from app.models.user import User
from app.services.audit_logger import AuditLogger
from app.services.customer_sync_service import CustomerSyncService
from app.services.fincode.client import FincodeClient


class BaseManager(ABC):
    """Manager 共通の依存（fincode クライアント・監査・顧客同期）を保持する抽象基底。"""

    def __init__(self, client: FincodeClient, audit: AuditLogger | None = None) -> None:
        self._client = client
        self._audit = audit or AuditLogger()
        self._customers = CustomerSyncService(client)

    @property
    @abstractmethod
    def auditable_type(self) -> str:
        """この Manager が監査ログへ記録するリソース種別。サブクラスが定義する。"""

    async def _get_owned_card(self, db: AsyncSession, user: User, card_id: int) -> FincodeCard:
        """取得 + 所有 + soft delete チェックを一括で行い、使えるカード行を返す。

        他ユーザーのカードも「存在しない」扱いに統一する。403 を返すと連番 ID に
        対してカードの存在有無を露呈してしまう（ID 列挙対策）。
        """
        card = await db.get(FincodeCard, card_id)
        if card is None or card.deleted_at is not None or card.user_id != user.id:
            raise NotFoundError(code="card_not_found")
        return card
