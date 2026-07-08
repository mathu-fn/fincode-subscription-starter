"""認可境界（IDOR）: 他ユーザーのリソースへのアクセス拒否。

実際に 2 人目のユーザーを作り、他人のカードを削除・契約に使えないことを
API 境界で検証する（ガードを消すとここが落ちる）。応答は 403 ではなく
404 (card_not_found) — 403 を返すと連番 ID に対してカードの存在有無を
露呈してしまうため、「存在しない」扱いに統一している（ID 列挙対策）。
"""

from __future__ import annotations

from typing import Any

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import FakeFincodeClient


@pytest_asyncio.fixture()
async def second_user_headers(db_session: AsyncSession) -> dict[str, str]:
    from app.core.security import create_access_token
    from app.models.user import User

    user = User(google_sub="fixture-google-sub-2", email="mallory@example.com", name="Second User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


async def _create_card_as_first_user(auth_client: AsyncClient) -> int:
    card = await auth_client.post("/api/subscription/cards", json={"token": "tok_test_owner"})
    assert card.status_code == 201, card.text
    return int(card.json()["id"])


async def test_cannot_delete_other_users_card(
    auth_client: AsyncClient,
    fake_fincode: FakeFincodeClient,
    second_user_headers: dict[str, str],
) -> None:
    card_id = await _create_card_as_first_user(auth_client)

    response = await auth_client.delete(
        f"/api/subscription/cards/{card_id}", headers=second_user_headers
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"]["code"] == "card_not_found"

    # 所有者のカード一覧には残っている（削除されていない）。
    listed = await auth_client.get("/api/subscription/cards")
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [card_id]


async def test_cannot_subscribe_with_other_users_card(
    auth_client: AsyncClient,
    fake_fincode: FakeFincodeClient,
    second_user_headers: dict[str, str],
) -> None:
    card_id = await _create_card_as_first_user(auth_client)
    calls_before: list[Any] = list(fake_fincode.calls)

    response = await auth_client.post(
        "/api/subscription",
        json={"fincode_plan_id": "plan_test_pro", "card_id": card_id},
        headers=second_user_headers,
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"]["code"] == "card_not_found"
    # fincode の契約作成には到達していない。
    assert ("POST", "/v1/subscriptions") not in fake_fincode.calls[len(calls_before) :]
