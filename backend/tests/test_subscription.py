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
        # クエリ/ボディまで検証したい新テスト向けに、リクエスト全体も並行記録する
        # （既存の ``calls`` 2タプル assert は壊さない）。
        self.requests: list[dict[str, Any]] = []

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((method, path))
        self.requests.append({"method": method, "path": path, "params": params, "json": json})
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


def _find_request(fake: FakeFincodeClient, method: str, path: str) -> dict[str, Any]:
    matches = [r for r in fake.requests if r["method"] == method and r["path"] == path]
    assert matches, f"no recorded {method} {path}; got {fake.requests}"
    return matches[-1]


async def test_cancel_paid_plan_sends_pay_type_query(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # fincode の解約は ``DELETE /v1/subscriptions/{id}?pay_type=Card``。クエリが無いと 400。
    await _create_paid_subscription(auth_client)

    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 200, cancel.text

    req = _find_request(fake_fincode, "DELETE", "/v1/subscriptions/sub_test_1")
    assert req["params"] == {"pay_type": "Card"}
    assert req["json"] is None


async def test_change_paid_to_paid_plan_recreates_subscription(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # fincode は課金開始済みサブスクのプラン変更（PUT）を拒否する（ESC03194031）。
    # そのため有料→有料は「現行サブスクを解約（DELETE, pay_type クエリ付き）→新プランで
    # 再作成（POST）」で行い、同じローカル行を更新する。PUT は呼ばない。
    await _create_paid_subscription(auth_client)
    fake_fincode.requests.clear()

    change = await auth_client.patch(
        "/api/subscription", json={"fincode_plan_id": "plan_test_basic"}
    )
    assert change.status_code == 200, change.text
    assert change.json()["fincode_plan_id"] == "plan_test_basic"

    # 旧サブスクの解約はクエリ pay_type=Card 付き。
    cancel = _find_request(fake_fincode, "DELETE", "/v1/subscriptions/sub_test_1")
    assert cancel["params"] == {"pay_type": "Card"}
    # 新プランで再作成（POST）。新サブスクのボディに新プランIDが入る。
    create = _find_request(fake_fincode, "POST", "/v1/subscriptions")
    assert create["json"]["plan_id"] == "plan_test_basic"
    # プラン変更で PUT は一切呼ばない。
    assert not any(r["method"] == "PUT" for r in fake_fincode.requests)


async def test_change_paid_to_free_plan_cancels_with_pay_type_query(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # 有料→フリーは fincode サブスクを解約（DELETE, pay_type クエリ付き）し、ローカル行を
    # フリースナップショットへ更新して fincode_subscription_id を外す。
    await _create_paid_subscription(auth_client)

    change = await auth_client.patch("/api/subscription", json={"fincode_plan_id": "free"})
    assert change.status_code == 200, change.text
    body = change.json()
    assert body["fincode_plan_id"] == "free"
    assert body["status"] == "active"
    assert body["fincode_subscription_id"] is None

    req = _find_request(fake_fincode, "DELETE", "/v1/subscriptions/sub_test_1")
    assert req["params"] == {"pay_type": "Card"}
