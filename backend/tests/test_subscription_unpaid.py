"""未払い（unpaid）契約の取り扱い。

unpaid は fincode 側のサブスクが生きたままの「使用中契約」なので、
新規契約をブロックし（アプリ層 409 + partial unique index）、
プラン変更・解約・カード保護の各フローが unpaid 契約にも作用することを検証する。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from tests.test_subscription import FakeFincodeClient


@pytest_asyncio.fixture()
async def fake_fincode(app_instance) -> FakeFincodeClient:
    from app.api.deps import get_fincode_client

    fake = FakeFincodeClient()
    app_instance.dependency_overrides[get_fincode_client] = lambda: fake
    return fake


async def _create_unpaid_subscription(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    *,
    current_period_end: datetime | None = None,
    cancelled_at: datetime | None = None,
) -> Subscription:
    """有料契約を API 経由で作成し、DB 上で unpaid に落とす（支払い失敗後の状態）。"""
    card = await auth_client.post("/api/subscription/cards", json={"token": "tok_test_unpaid"})
    assert card.status_code == 201, card.text
    create = await auth_client.post(
        "/api/subscription",
        json={"fincode_plan_id": "plan_test_pro", "card_id": card.json()["id"]},
    )
    assert create.status_code == 201, create.text

    sub = await db_session.scalar(
        select(Subscription).where(Subscription.fincode_subscription_id == "sub_test_1")
    )
    assert sub is not None
    sub.status = SubscriptionStatus.UNPAID
    sub.current_period_end = current_period_end
    sub.cancelled_at = cancelled_at
    await db_session.commit()
    return sub


async def test_subscribe_returns_409_while_unpaid(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    await _create_unpaid_subscription(auth_client, db_session)

    response = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "active_subscription_exists"


async def test_unique_index_blocks_active_row_alongside_unpaid(
    db_session, registered_user: dict[str, Any]
) -> None:
    # アプリ層ガードをすり抜けても DB の partial unique index
    # （status IN ('active','unpaid')）が二重契約を拒否する。
    user_id = registered_user["user"]["id"]

    def _row(status: SubscriptionStatus, suffix: str) -> Subscription:
        return Subscription(
            user_id=user_id,
            fincode_subscription_id=f"sub_dup_{suffix}",
            nonce=f"nonce-dup-{suffix}",
            fincode_plan_id="plan_test_pro",
            plan_name="Pro",
            plan_amount=500,
            plan_interval="month",
            status=status,
        )

    db_session.add(_row(SubscriptionStatus.UNPAID, "unpaid"))
    await db_session.flush()

    db_session.add(_row(SubscriptionStatus.ACTIVE, "active"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_get_subscription_returns_unpaid(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    await _create_unpaid_subscription(auth_client, db_session)

    response = await auth_client.get("/api/subscription")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "unpaid"


async def test_change_plan_recovers_unpaid_to_active(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    # 復帰経路: unpaid 中でもプラン変更でき、確定時に active へ戻る
    # （fincode 側は旧サブスク解約 + 新プランで再作成）。
    await _create_unpaid_subscription(auth_client, db_session)

    change = await auth_client.patch(
        "/api/subscription", json={"fincode_plan_id": "plan_test_basic"}
    )
    assert change.status_code == 200, change.text
    body = change.json()
    assert body["status"] == "active"
    assert body["fincode_plan_id"] == "plan_test_basic"
    assert ("DELETE", "/v1/subscriptions/sub_test_1") in fake_fincode.calls


async def test_change_plan_to_free_exits_unpaid(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    await _create_unpaid_subscription(auth_client, db_session)

    change = await auth_client.patch("/api/subscription", json={"fincode_plan_id": "free"})
    assert change.status_code == 200, change.text
    body = change.json()
    assert body["status"] == "active"
    assert body["fincode_plan_id"] == "free"
    assert body["fincode_subscription_id"] is None
    assert ("DELETE", "/v1/subscriptions/sub_test_1") in fake_fincode.calls


async def test_cancel_unpaid_subscription(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    # 離脱経路: unpaid 契約は解約でき、支払い済みの未来期間が無ければ即 cancelled。
    await _create_unpaid_subscription(auth_client, db_session)

    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"
    assert ("DELETE", "/v1/subscriptions/sub_test_1") in fake_fincode.calls


async def test_delete_card_conflicts_while_unpaid(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    # unpaid 契約が参照するカードは fincode がリトライ課金に使うため削除不可。
    sub = await _create_unpaid_subscription(auth_client, db_session)
    assert sub.fincode_card_id is not None

    response = await auth_client.delete(f"/api/subscription/cards/{sub.fincode_card_id}")
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "card_in_use"


async def test_finalize_elapsed_unpaid_cancellation_unblocks_new_subscription(
    auth_client: AsyncClient, db_session, fake_fincode: FakeFincodeClient
) -> None:
    # 解約予約中に unpaid へ落ちた契約は期間満了で cancelled に遅延確定され、
    # partial unique index の「幽霊ブロック」にならず新規契約できる。
    old = await _create_unpaid_subscription(
        auth_client,
        db_session,
        current_period_end=datetime(2000, 1, 1, tzinfo=UTC),
        cancelled_at=datetime(2000, 1, 1, tzinfo=UTC),
    )

    create = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert create.status_code == 201, create.text
    assert create.json()["status"] == "active"

    await db_session.refresh(old)
    assert old.status == SubscriptionStatus.CANCELLED
