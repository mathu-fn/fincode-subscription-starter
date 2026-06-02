"""0円フリープラン（アプリ側で合成・ローカル完結）のサブスクリプション挙動。

fincode は CLAUDE.md の方針どおり直接叩かず、``get_fincode_client`` をフェイクに
差し替える。フェイクは呼び出しを記録するので、フリープランの契約・解約が fincode を
一切呼ばないことを検証できる。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.subscription import Subscription

CURRENT_PERIOD_END = "2099-01-01T00:00:00+00:00"


class FakeFincodeClient:
    """``FincodeClient`` プロトコルの最小フェイク。呼び出しを記録する。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((method, path))
        if method == "GET" and path == "/v1/plans":
            return {"list": []}
        if method == "GET" and path.startswith("/v1/plans/"):
            return {
                "id": path.rsplit("/", 1)[-1],
                "plan_name": "Pro",
                "amount": "500",
                "interval_pattern": "month",
            }
        if method == "POST" and path == "/v1/customers":
            return {"id": json["id"] if json else "local_user_1"}
        if method == "POST" and path.endswith("/cards"):
            return {
                "id": "card_test_1",
                "brand": "VISA",
                "card_no": "************4242",
                "expire": "3012",
                "default_flag": "1",
            }
        if method == "POST" and path == "/v1/subscriptions":
            return {
                "id": "sub_test_1",
                "status": "ACTIVE",
                "current_period_end": CURRENT_PERIOD_END,
            }
        if method == "DELETE" and path == "/v1/subscriptions/sub_test_1":
            return {"id": "sub_test_1", "status": "CANCELED"}
        raise AssertionError(f"unexpected fincode call: {method} {path}")


@pytest_asyncio.fixture()
async def fake_fincode(app_instance) -> FakeFincodeClient:
    from app.api.deps import get_fincode_client

    fake = FakeFincodeClient()
    app_instance.dependency_overrides[get_fincode_client] = lambda: fake
    return fake


async def test_list_plans_includes_free_plan(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # fincode が空のプラン一覧を返しても、フリープランは先頭に現れる。
    response = await auth_client.get("/api/subscription/plans")
    assert response.status_code == 200, response.text
    plans = response.json()
    assert plans[0]["fincode_plan_id"] == "free"
    assert plans[0]["amount"] == 0
    assert plans[0]["currency"] == "JPY"


async def test_subscribe_free_plan_without_card(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # カード未登録でもフリープランは契約できる。fincode は一切呼ばれない。
    response = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["fincode_plan_id"] == "free"
    assert body["plan_amount"] == 0
    assert body["status"] == "active"
    assert body["fincode_subscription_id"] is None
    assert fake_fincode.calls == []


async def test_subscribe_paid_plan_requires_card(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # 有料プランをカード無しで契約しようとすると 422 (card_required)。
    response = await auth_client.post(
        "/api/subscription", json={"fincode_plan_id": "plan_test_pro"}
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "card_required"


async def test_cancel_free_plan_is_local_only(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    create = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert create.status_code == 201, create.text

    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"
    assert cancel.json()["cancel_at_period_end"] is False
    # 契約・解約のどちらでも fincode は呼ばれていない。
    assert fake_fincode.calls == []


async def test_free_plan_occupies_single_active_slot(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    first = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert first.status_code == 201, first.text

    second = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert second.status_code == 409, second.text
    assert second.json()["detail"]["code"] == "active_subscription_exists"


async def _create_paid_subscription(auth_client: AsyncClient) -> dict[str, Any]:
    card = await auth_client.post("/api/subscription/cards", json={"token": "tok_test_paid"})
    assert card.status_code == 201, card.text

    create = await auth_client.post(
        "/api/subscription",
        json={"fincode_plan_id": "plan_test_pro", "card_id": card.json()["id"]},
    )
    assert create.status_code == 201, create.text
    return cast(dict[str, Any], create.json())


async def test_cancel_paid_plan_keeps_access_until_current_period_end(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    created = await _create_paid_subscription(auth_client)
    assert created["status"] == "active"
    assert created["current_period_end"].startswith("2099-01-01T00:00:00")

    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 200, cancel.text
    body = cancel.json()
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is True
    assert body["cancelled_at"] is not None
    assert body["current_period_end"].startswith("2099-01-01T00:00:00")

    current = await auth_client.get("/api/subscription")
    assert current.status_code == 200, current.text
    assert current.json()["cancel_at_period_end"] is True

    change = await auth_client.patch(
        "/api/subscription", json={"fincode_plan_id": "plan_test_basic"}
    )
    assert change.status_code == 409, change.text
    assert change.json()["detail"]["code"] == "subscription_cancel_scheduled"
    assert ("DELETE", "/v1/subscriptions/sub_test_1") in fake_fincode.calls


async def test_elapsed_cancel_scheduled_subscription_does_not_block_new_subscription(
    auth_client: AsyncClient,
    db_session,
    fake_fincode: FakeFincodeClient,
) -> None:
    await _create_paid_subscription(auth_client)
    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 200, cancel.text

    sub = await db_session.scalar(
        select(Subscription).where(Subscription.fincode_subscription_id == "sub_test_1")
    )
    assert sub is not None
    sub.current_period_end = datetime(2000, 1, 1, tzinfo=UTC)
    await db_session.commit()

    create = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["fincode_plan_id"] == "free"
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is False
    assert ("DELETE", "/v1/subscriptions/sub_test_1") in fake_fincode.calls
