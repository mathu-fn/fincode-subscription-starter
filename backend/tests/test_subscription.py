"""0円フリープラン（アプリ側で合成・ローカル完結）のサブスクリプション挙動。

fincode は CLAUDE.md の方針どおり直接叩かず、``get_fincode_client`` をフェイクに
差し替える。フェイクは呼び出しを記録するので、フリープランの契約・解約が fincode を
一切呼ばないことを検証できる。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from httpx import AsyncClient
from sqlalchemy import select

from app.models.subscription import Subscription
from tests.conftest import CURRENT_PERIOD_END, FakeFincodeClient  # noqa: F401


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


async def test_subscribe_with_missing_card_returns_card_not_found(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # 存在しないカード ID での契約は 404 (card_not_found)。
    # subscription_not_found と取り違えない（コードとメッセージの整合性）。
    response = await auth_client.post(
        "/api/subscription", json={"fincode_plan_id": "plan_test_pro", "card_id": 999999}
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"]["code"] == "card_not_found"


async def test_cancel_free_plan_is_local_only(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient, db_session
) -> None:
    create = await auth_client.post("/api/subscription", json={"fincode_plan_id": "free"})
    assert create.status_code == 201, create.text

    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"
    assert cancel.json()["cancel_at_period_end"] is False
    # 契約・解約のどちらでも fincode は呼ばれていない。
    assert fake_fincode.calls == []

    # フリープラン解約も有料解約と同様に監査ログを残す。
    from app.models.audit_log import AuditLog

    audit = await db_session.scalar(select(AuditLog).where(AuditLog.event == "subscription.cancel"))
    assert audit is not None
    assert audit.after["status"] == "cancelled"
    assert audit.after["cancelled_at"] is not None


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


async def test_subscribe_sends_start_date_in_jst(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # fincode の日付境界は JST。UTC で日付を作ると JST 0:00〜8:59 に前日の
    # start_date を送ってしまい、過去日として拒否される。
    from app.services.fincode.base import FINCODE_TIMEZONE

    before = datetime.now(FINCODE_TIMEZONE).strftime("%Y/%m/%d")
    await _create_paid_subscription(auth_client)
    after = datetime.now(FINCODE_TIMEZONE).strftime("%Y/%m/%d")

    req = _find_request(fake_fincode, "POST", "/v1/subscriptions")
    # JST 深夜 0:00 をまたいだ場合だけ before と after が異なるため、両方許容する。
    assert req["json"]["start_date"] in {before, after}


async def test_plan_fetch_transient_error_returns_503_not_422(
    auth_client: AsyncClient, app_instance
) -> None:
    # fincode 障害（5xx）中の契約は「プランが利用できない」（422 plan_unavailable）
    # ではなく、一時的エラーとして 503 で返す（CLAUDE.md のエラーマッピング）。
    from app.api.deps import get_fincode_client
    from app.core.exceptions import FincodeServerError

    class TransientFailureFincodeClient(FakeFincodeClient):
        async def request(
            self,
            method: str,
            path: str,
            *,
            json: dict[str, Any] | None = None,
            params: dict[str, str] | None = None,
            idempotency_key: str | None = None,
        ) -> dict[str, Any]:
            if method == "GET" and path.startswith("/v1/plans/"):
                raise FincodeServerError()
            return await super().request(
                method, path, json=json, params=params, idempotency_key=idempotency_key
            )

    fake = TransientFailureFincodeClient()
    app_instance.dependency_overrides[get_fincode_client] = lambda: fake

    response = await auth_client.post(
        "/api/subscription", json={"fincode_plan_id": "plan_test_pro"}
    )
    assert response.status_code == 503, response.text
    assert response.json()["detail"]["code"] == "fincode_server_error"


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


async def test_subscribe_replays_same_idempotency_key_without_new_charge(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    # レスポンス消失後のクライアントリトライ（同一 Idempotency-Key の再 POST）は
    # 新しい fincode 契約を作らず、以前成功した契約をそのまま返す（二重課金防止）。
    card = await auth_client.post("/api/subscription/cards", json={"token": "tok_test_replay"})
    assert card.status_code == 201, card.text
    payload = {"fincode_plan_id": "plan_test_pro", "card_id": card.json()["id"]}
    headers = {"Idempotency-Key": "replay-key-1"}

    first = await auth_client.post("/api/subscription", json=payload, headers=headers)
    assert first.status_code == 201, first.text

    second = await auth_client.post("/api/subscription", json=payload, headers=headers)
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]

    creates = [c for c in fake_fincode.calls if c == ("POST", "/v1/subscriptions")]
    assert len(creates) == 1


async def test_paid_subscription_freezes_plan_snapshot(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient, db_session
) -> None:
    # 契約時点の fincode プラン情報は plan_snapshot に JSONB で凍結保存される
    # （CLAUDE.md の必須不変条件。fincode 側のプラン変更から過去契約を守る）。
    created = await _create_paid_subscription(auth_client)

    sub = await db_session.get(Subscription, created["id"])
    assert sub is not None
    assert sub.plan_snapshot == {
        "id": "plan_test_pro",
        "plan_name": "Pro",
        "amount": "500",
        "interval_pattern": "month",
    }


async def test_subscribe_with_expired_card_returns_422(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient, db_session
) -> None:
    from app.models.fincode_card import FincodeCard

    card = await auth_client.post("/api/subscription/cards", json={"token": "tok_test_expired"})
    assert card.status_code == 201, card.text
    card_id = card.json()["id"]

    row = await db_session.get(FincodeCard, card_id)
    assert row is not None
    row.exp_year = 2020
    row.exp_month = 1
    await db_session.commit()

    response = await auth_client.post(
        "/api/subscription", json={"fincode_plan_id": "plan_test_pro", "card_id": card_id}
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "expired_card"


async def test_cancel_and_change_without_subscription_return_404(
    auth_client: AsyncClient, fake_fincode: FakeFincodeClient
) -> None:
    cancel = await auth_client.delete("/api/subscription")
    assert cancel.status_code == 404, cancel.text
    assert cancel.json()["detail"]["code"] == "subscription_not_found"

    change = await auth_client.patch("/api/subscription", json={"fincode_plan_id": "free"})
    assert change.status_code == 404, change.text
    assert change.json()["detail"]["code"] == "subscription_not_found"


async def test_billing_history_paginates_and_isolates_users(
    auth_client: AsyncClient,
    fake_fincode: FakeFincodeClient,
    db_session,
) -> None:
    from app.models.subscription_result import SubscriptionResult
    from app.models.user import User

    created = await _create_paid_subscription(auth_client)

    # 自分の課金結果 3 件 + 他ユーザーの結果 1 件を用意する。
    for i in range(3):
        db_session.add(
            SubscriptionResult(
                subscription_id=created["id"],
                fincode_subscription_id="sub_test_1",
                fincode_payment_id=f"pay_hist_{i}",
                status="succeeded",
                amount=500,
                charged_at=datetime(2026, 1, i + 1, tzinfo=UTC),
                fincode_response=None,
            )
        )
    other_user = User(google_sub="history-other", email="other@example.com", name="Other")
    db_session.add(other_user)
    await db_session.flush()
    other_sub = Subscription(
        user_id=other_user.id,
        fincode_subscription_id="sub_other_hist",
        nonce="nonce-other-hist",
        fincode_plan_id="plan_test_pro",
        plan_name="Pro",
        plan_amount=500,
        plan_interval="month",
        status="active",
    )
    db_session.add(other_sub)
    await db_session.flush()
    db_session.add(
        SubscriptionResult(
            subscription_id=other_sub.id,
            fincode_subscription_id="sub_other_hist",
            fincode_payment_id="pay_other",
            status="succeeded",
            amount=500,
            charged_at=datetime(2026, 1, 10, tzinfo=UTC),
            fincode_response=None,
        )
    )
    await db_session.commit()

    page1 = await auth_client.get("/api/subscription/history", params={"page": 1, "per_page": 2})
    assert page1.status_code == 200, page1.text
    body = page1.json()
    # total は自分の 3 件のみ（他ユーザーの pay_other は混ざらない）。
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["per_page"] == 2
    # charged_at 降順。
    assert [r["fincode_payment_id"] for r in body["data"]] == ["pay_hist_2", "pay_hist_1"]

    page2 = await auth_client.get("/api/subscription/history", params={"page": 2, "per_page": 2})
    assert page2.status_code == 200
    assert [r["fincode_payment_id"] for r in page2.json()["data"]] == ["pay_hist_0"]
