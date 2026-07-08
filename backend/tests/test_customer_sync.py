"""CustomerSyncService.ensure の耐障害分岐。

- 並行初回作成（TOCTOU）は IntegrityError を勝者の行の返却に翻訳する（500 にしない）
- fincode の 4xx（顧客既存など）は決定論的なローカル ID で続行する
- 一時的失敗（5xx 等）は再送出し、フェイク ID を永続化しない（キャッシュ汚染防止）
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FincodeApiError, FincodeServerError
from app.models.fincode_customer import FincodeCustomer
from app.models.user import User
from app.services.customer_sync_service import CustomerSyncService


class _FakeFincodeClient:
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        assert method == "POST" and path == "/v1/customers"
        return {"id": json["id"] if json else "local_user_x"}

    async def aclose(self) -> None:
        pass


async def test_ensure_recovers_from_concurrent_insert(
    db_session: AsyncSession,
    registered_user: dict[str, Any],
    monkeypatch,
) -> None:
    user = await db_session.get(User, registered_user["user"]["id"])
    assert user is not None

    # 勝者の行を先にコミットしておき、ensure の「事前 SELECT」だけを None に
    # 見せかけることで、SELECT と INSERT の間に割り込まれた状態を再現する。
    winner = FincodeCustomer(user_id=user.id, fincode_customer_id="cus_winner")
    db_session.add(winner)
    await db_session.commit()

    original_scalar = db_session.scalar
    call_count = 0

    async def scalar_with_stale_first_read(stmt: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None
        return await original_scalar(stmt, *args, **kwargs)

    monkeypatch.setattr(db_session, "scalar", scalar_with_stale_first_read)

    service = CustomerSyncService(_FakeFincodeClient())
    customer = await service.ensure(db_session, user)

    # IntegrityError を握りつぶさず勝者の行へ回復している。
    assert customer.fincode_customer_id == "cus_winner"
    assert call_count >= 2


class _RaisingFincodeClient:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        raise self._exc

    async def aclose(self) -> None:
        pass


async def test_ensure_transient_failure_does_not_persist_placeholder(
    db_session: AsyncSession,
    registered_user: dict[str, Any],
) -> None:
    # 5xx は「fincode に顧客が存在するか不明」。local_user_{id} を永続化すると
    # 以降のカード・契約呼び出しが存在しない顧客を参照し続けるため、再送出する。
    user = await db_session.get(User, registered_user["user"]["id"])
    assert user is not None

    service = CustomerSyncService(_RaisingFincodeClient(FincodeServerError()))
    with pytest.raises(FincodeServerError):
        await service.ensure(db_session, user)

    row = await db_session.scalar(select(FincodeCustomer).where(FincodeCustomer.user_id == user.id))
    assert row is None


async def test_ensure_4xx_reuses_deterministic_local_id(
    db_session: AsyncSession,
    registered_user: dict[str, Any],
) -> None:
    # 4xx（前回試行で fincode 側だけ作成済み等）は決定論的 ID で続行する。
    user = await db_session.get(User, registered_user["user"]["id"])
    assert user is not None

    service = CustomerSyncService(_RaisingFincodeClient(FincodeApiError()))
    customer = await service.ensure(db_session, user)
    assert customer.fincode_customer_id == f"local_user_{user.id}"
