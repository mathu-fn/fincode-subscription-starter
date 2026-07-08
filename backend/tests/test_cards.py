"""カード CRUD: 一覧・登録・soft delete。

「カードは物理削除せず ``deleted_at`` を立てる」という不変条件を、
API 応答と DB 状態の両面から検証する。
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.fincode_card import FincodeCard
from tests.conftest import FakeFincodeClient


async def test_card_lifecycle_is_soft_delete(
    auth_client: AsyncClient,
    fake_fincode: FakeFincodeClient,
    db_session: AsyncSession,
) -> None:
    created = await auth_client.post("/api/subscription/cards", json={"token": "tok_test_life"})
    assert created.status_code == 201, created.text
    card_id = created.json()["id"]
    assert created.json()["brand"] == "VISA"
    assert created.json()["last4"] == "4242"

    listed = await auth_client.get("/api/subscription/cards")
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [card_id]

    deleted = await auth_client.delete(f"/api/subscription/cards/{card_id}")
    assert deleted.status_code == 204, deleted.text
    # fincode 側の削除も呼ばれている。
    assert any(m == "DELETE" and "/cards/" in p for m, p in fake_fincode.calls)

    # 物理削除ではなく deleted_at が立つ（過去契約・監査ログの説明可能性を残す）。
    row = await db_session.get(FincodeCard, card_id)
    assert row is not None
    assert row.deleted_at is not None

    # 一覧からは除外される。
    listed_after = await auth_client.get("/api/subscription/cards")
    assert listed_after.status_code == 200
    assert listed_after.json() == []

    # 削除済みカードへの再削除は 404。
    again = await auth_client.delete(f"/api/subscription/cards/{card_id}")
    assert again.status_code == 404
    assert again.json()["detail"]["code"] == "card_not_found"

    # 登録・削除の両方が監査されている。
    events = (
        (
            await db_session.execute(
                select(AuditLog.event).where(AuditLog.auditable_type == "fincode_card")
            )
        )
        .scalars()
        .all()
    )
    assert sorted(events) == ["card.create", "card.delete"]
