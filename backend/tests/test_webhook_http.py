"""Webhook の HTTP 境界: 署名検証・ヘッダ抽出・応答コード。

ハンドラー単体は test_webhook_payment.py / test_webhook_cancellation.py が
検証済み。ここでは ``POST /api/webhooks/fincode`` を実際に叩き、
Fincode-Signature ヘッダの取り扱いとステータスコードの契約を固定する。
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from httpx import AsyncClient

# conftest.py が FINCODE_WEBHOOK_SECRET=test-webhook-secret を設定している。
WEBHOOK_SECRET = "test-webhook-secret"


def _sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode()


async def test_valid_signature_returns_204(client: AsyncClient) -> None:
    body = _body({"event_id": "evt_http_ok", "event": "some.unknown.event", "data": {}})
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": _sign(body), "Content-Type": "application/json"},
    )
    # 未知イベントも dlq_reason 付きで受理して 204（fincode の再送を止める）。
    assert response.status_code == 204, response.text


async def test_invalid_signature_returns_401(client: AsyncClient) -> None:
    body = _body({"event_id": "evt_http_bad_sig", "event": "payment.succeeded", "data": {}})
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": "0" * 64, "Content-Type": "application/json"},
    )
    assert response.status_code == 401, response.text
    assert response.json()["detail"]["code"] == "invalid_webhook_signature"


async def test_missing_signature_returns_401(client: AsyncClient) -> None:
    body = _body({"event_id": "evt_http_no_sig", "event": "payment.succeeded", "data": {}})
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401, response.text
    assert response.json()["detail"]["code"] == "invalid_webhook_signature"


async def test_oversized_body_returns_413(client: AsyncClient) -> None:
    # 未認証・レート制限なしのエンドポイントなので、署名検証以前にサイズで打ち切る。
    body = b'{"_pad":"' + b"A" * (64 * 1024 + 1) + b'"}'
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": _sign(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 413, response.text
    assert response.json()["detail"]["code"] == "payload_too_large"


async def test_missing_event_id_returns_422(client: AsyncClient) -> None:
    body = _body({"event": "payment.succeeded", "data": {}})
    response = await client.post(
        "/api/webhooks/fincode",
        content=body,
        headers={"Fincode-Signature": _sign(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "invalid_webhook_payload"
