"""0円フリープラン（アプリ側で合成・ローカル完結）のサブスクリプション挙動。

fincode は CLAUDE.md の方針どおり直接叩かず、``get_fincode_client`` をフェイクに
差し替える。フェイクは呼び出しを記録するので、フリープランの契約・解約が fincode を
一切呼ばないことを検証できる。
"""

from __future__ import annotations

from typing import Any

import pytest_asyncio
from httpx import AsyncClient


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
