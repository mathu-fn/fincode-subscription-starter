"""Webhook の HTTP 境界: 署名検証・ヘッダ抽出・応答コード。

ハンドラー単体は test_webhook_payment.py / test_webhook_cancellation.py が
検証済み。ここでは ``POST /api/webhooks/fincode`` を実際に叩き、
Fincode-Signature ヘッダの取り扱いとステータスコードの契約を固定する。
"""

from __future__ import annotations

from httpx import AsyncClient

# 署名ヘルパーは conftest に集約されている（FINCODE_WEBHOOK_SECRET も同じ定数から設定）。
from tests.conftest import signed_payload


async def test_valid_signature_returns_204(client: AsyncClient) -> None:
    body, signature = signed_payload(
        {"event_id": "evt_http_ok", "event": "some.unknown.event", "data": {}}
    )
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": signature, "Content-Type": "application/json"},
    )
    # 未知イベントも dlq_reason 付きで受理して 204（fincode の再送を止める）。
    assert response.status_code == 204, response.text


async def test_invalid_signature_returns_401(client: AsyncClient) -> None:
    body, _ = signed_payload(
        {"event_id": "evt_http_bad_sig", "event": "payment.succeeded", "data": {}}
    )
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": "0" * 64, "Content-Type": "application/json"},
    )
    assert response.status_code == 401, response.text
    assert response.json()["detail"]["code"] == "invalid_webhook_signature"


async def test_missing_signature_returns_401(client: AsyncClient) -> None:
    body, _ = signed_payload(
        {"event_id": "evt_http_no_sig", "event": "payment.succeeded", "data": {}}
    )
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401, response.text
    assert response.json()["detail"]["code"] == "invalid_webhook_signature"


async def test_missing_event_id_returns_422(client: AsyncClient) -> None:
    body, signature = signed_payload({"event": "payment.succeeded", "data": {}})
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "invalid_webhook_payload"
