"""Webhook 本文サイズ上限（``_read_limited_body``）の単体テスト。

DB を必要とせず、未認証・レート制限なしのエンドポイントに巨大ボディを流し込む
メモリ枯渇 DoS を、署名検証以前に打ち切ることを検証する。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.routes.webhooks import _MAX_WEBHOOK_BODY_BYTES, _read_limited_body
from app.core.exceptions import PayloadTooLargeError


def _make_request(body: bytes, content_length: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if content_length is not None:
        headers.append((b"content-length", content_length.encode()))
    scope = {"type": "http", "method": "POST", "path": "/", "headers": headers}
    delivered = False

    async def receive() -> dict[str, object]:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


async def test_rejects_oversized_content_length() -> None:
    # Content-Length で申告された時点で、本文を読む前に弾く。
    request = _make_request(b"x", content_length=str(_MAX_WEBHOOK_BODY_BYTES + 1))
    with pytest.raises(PayloadTooLargeError):
        await _read_limited_body(request, _MAX_WEBHOOK_BODY_BYTES)


async def test_rejects_oversized_stream_without_content_length() -> None:
    # Content-Length を申告しない（chunked 等）場合も、実ストリームを上限で打ち切る。
    big = b"a" * (_MAX_WEBHOOK_BODY_BYTES + 1)
    request = _make_request(big)
    with pytest.raises(PayloadTooLargeError):
        await _read_limited_body(request, _MAX_WEBHOOK_BODY_BYTES)


async def test_accepts_small_body() -> None:
    request = _make_request(b'{"ok":true}')
    body = await _read_limited_body(request, _MAX_WEBHOOK_BODY_BYTES)
    assert body == b'{"ok":true}'
