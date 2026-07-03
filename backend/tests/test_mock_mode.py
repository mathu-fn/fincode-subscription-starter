"""``FINCODE_MODE=mock`` のモッククライアントと依存配線のテスト。

fincode アカウント無しでカード登録〜契約まで通ることを、実 HTTP を一切使わずに検証する。
"""

from __future__ import annotations

from typing import Any

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select

from app.api.deps import get_fincode_client
from app.core.config import Settings
from app.core.lifespan import create_fincode_client
from app.models.subscription import Subscription
from app.services.fincode.client import FincodeHttpClient
from app.services.fincode.mock_client import FincodeMockClient


def test_get_fincode_client_returns_mock_when_mode_mock() -> None:
    client = create_fincode_client(Settings(fincode_mode="mock"))
    assert isinstance(client, FincodeMockClient)


def test_get_fincode_client_returns_http_client_by_default() -> None:
    client = create_fincode_client(Settings(fincode_mode="live"))
    assert isinstance(client, FincodeHttpClient)


def test_fincode_mock_enabled_is_case_insensitive() -> None:
    assert Settings(fincode_mode="MOCK").fincode_mock_enabled is True
    assert Settings(fincode_mode=" mock ").fincode_mock_enabled is True
    assert Settings(fincode_mode="live").fincode_mock_enabled is False


async def test_mock_client_lists_and_fetches_plans() -> None:
    client = FincodeMockClient()
    listed = await client.request("GET", "/v1/plans")
    ids = {p["id"] for p in listed["list"]}
    assert {"plan_mock_basic", "plan_mock_pro"} <= ids

    one = await client.request("GET", "/v1/plans/plan_mock_basic")
    assert one["id"] == "plan_mock_basic"
    assert one["delete_flag"] == "0"


async def test_mock_client_card_is_deterministic_per_token() -> None:
    client = FincodeMockClient()
    a = await client.request("POST", "/v1/customers/customer_mock/cards", json={"token": "tok_a"})
    again = await client.request(
        "POST", "/v1/customers/customer_mock/cards", json={"token": "tok_a"}
    )
    b = await client.request("POST", "/v1/customers/customer_mock/cards", json={"token": "tok_b"})

    assert a["id"].startswith("card_mock_")
    assert a["brand"] in {"VISA", "Mastercard", "JCB", "AMEX"}
    assert len(a["card_no"][-4:]) == 4
    # 同じトークンは同じカード、別トークンは（基本的に）別カードになる。
    assert a == again
    assert a["id"] != b["id"]


async def test_mock_client_creates_subscription_with_mock_id() -> None:
    client = FincodeMockClient()
    raw = await client.request(
        "POST", "/v1/subscriptions", json={"plan_id": "plan_mock_basic"}, idempotency_key="n1"
    )
    assert raw["id"].startswith("sub_mock_")
    assert raw["status"] == "active"
    assert raw["current_period_end"]


@pytest_asyncio.fixture()
async def mock_fincode(app_instance) -> FincodeMockClient:
    mock = FincodeMockClient()
    app_instance.dependency_overrides[get_fincode_client] = lambda: mock
    return mock


async def test_full_card_then_paid_subscription_flow_in_mock_mode(
    auth_client: AsyncClient, mock_fincode: FincodeMockClient
) -> None:
    # プラン一覧にモックプランが出る。
    plans = (await auth_client.get("/api/subscription/plans")).json()
    plan_ids = {p["fincode_plan_id"] for p in plans}
    assert "plan_mock_basic" in plan_ids

    # カード登録（fincode UI を介さず、ダミートークンを直接 POST）。
    card_resp = await auth_client.post("/api/subscription/cards", json={"token": "tok_mock_visa"})
    assert card_resp.status_code == 201, card_resp.text
    card: dict[str, Any] = card_resp.json()
    assert card["last4"] and card["brand"]

    # 有料プランの契約が成功し、fincode 契約 ID にモック ID が入る。
    sub_resp = await auth_client.post(
        "/api/subscription",
        json={"fincode_plan_id": "plan_mock_basic", "card_id": card["id"]},
    )
    assert sub_resp.status_code == 201, sub_resp.text
    sub = sub_resp.json()
    assert sub["status"] == "active"
    assert sub["plan_amount"] == 500
    assert sub["fincode_subscription_id"].startswith("sub_mock_")


async def test_paid_subscription_plan_change_updates_same_active_row(
    auth_client: AsyncClient, mock_fincode: FincodeMockClient, db_session
) -> None:
    card_resp = await auth_client.post("/api/subscription/cards", json={"token": "tok_mock_visa"})
    assert card_resp.status_code == 201, card_resp.text
    card: dict[str, Any] = card_resp.json()

    create_resp = await auth_client.post(
        "/api/subscription",
        json={"fincode_plan_id": "plan_mock_basic", "card_id": card["id"]},
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    change_resp = await auth_client.patch(
        "/api/subscription",
        json={"fincode_plan_id": "plan_mock_pro"},
        headers={"Idempotency-Key": "change-plan-1"},
    )
    assert change_resp.status_code == 200, change_resp.text
    changed = change_resp.json()
    # ローカル行は同じものを使い回す（id 不変・行数は 1 のまま）。
    assert changed["id"] == created["id"]
    # 一方 fincode サブスクは作り直されるため ID は変わる（fincode は課金開始済み
    # サブスクのプラン変更を拒否するので、解約→新プランで再作成する）。
    assert changed["fincode_subscription_id"] != created["fincode_subscription_id"]
    assert changed["fincode_subscription_id"].startswith("sub_mock_")
    assert changed["fincode_plan_id"] == "plan_mock_pro"
    assert changed["plan_amount"] == 1500

    total = await db_session.scalar(select(func.count()).select_from(Subscription))
    assert total == 1


async def test_free_subscription_can_change_to_paid_plan_same_active_row(
    auth_client: AsyncClient, mock_fincode: FincodeMockClient, db_session
) -> None:
    free_resp = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert free_resp.status_code == 201, free_resp.text
    free_sub = free_resp.json()

    card_resp = await auth_client.post("/api/subscription/cards", json={"token": "tok_mock_visa"})
    assert card_resp.status_code == 201, card_resp.text
    card: dict[str, Any] = card_resp.json()

    change_resp = await auth_client.patch(
        "/api/subscription",
        json={"fincode_plan_id": "plan_mock_basic", "card_id": card["id"]},
    )
    assert change_resp.status_code == 200, change_resp.text
    changed = change_resp.json()
    assert changed["id"] == free_sub["id"]
    assert changed["fincode_subscription_id"].startswith("sub_mock_")
    assert changed["fincode_plan_id"] == "plan_mock_basic"
    assert changed["plan_amount"] == 500

    total = await db_session.scalar(select(func.count()).select_from(Subscription))
    assert total == 1
