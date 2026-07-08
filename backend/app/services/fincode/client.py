"""fincode HTTP クライアント。

``httpx.AsyncClient`` に Idempotency-Key・5xx/タイムアウト時のリトライ・
サーキットブレーカーをラップする。HTTP 429 / 4xx はリトライせず、
ブレーカーも反転させない。

生の fincode レスポンスボディは API 呼び出し元へ返さない。このクラスのメソッドは
成功時には解析済み JSON 辞書を返し、失敗時には型付き例外
（``FincodeApiError`` とそのサブクラス）を発生させる。
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, cast

import httpx

from app.core.exceptions import (
    FincodeApiError,
    FincodeRateLimitError,
    FincodeServerError,
    FincodeTimeoutError,
)
from app.core.logging import get_logger
from app.services.fincode.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


def _extract_fincode_error(response: httpx.Response) -> tuple[str | None, str | None]:
    """fincode のエラーレスポンスから ``error_code`` / ``error_message`` を防御的に取り出す。

    fincode のエラー本文は ``{"errors": [{"error_code", "error_message"}], "message"?}``
    形式（公式 SDK fincode-sdk-node の APIErrorResponse 型）。本文が JSON でない・想定キーが
    無い場合は ``(None, None)`` を返し、呼び出し側のログを妨げない。生レスポンス全体は
    返さない（クライアントへ漏らさない・ログにも丸ごと出さないため）。
    """
    try:
        data = response.json()
    except ValueError:
        return None, None
    if not isinstance(data, dict):
        return None, None
    errors = data.get("errors")
    if isinstance(errors, list) and errors and isinstance(errors[0], dict):
        first = errors[0]
        code = first.get("error_code")
        message = first.get("error_message")
        return (
            str(code) if code is not None else None,
            str(message) if message is not None else None,
        )
    message = data.get("message")
    return None, str(message) if message is not None else None


class FincodeClient(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class FincodeHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        tenant_shop_id: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
        breaker: CircuitBreaker | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if tenant_shop_id:
            headers["Tenant-Shop-Id"] = tenant_shop_id
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self._max_retries = max_retries
        self._breaker = breaker or CircuitBreaker()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            self._breaker.before_call()

            try:
                response = await self._client.request(
                    method, path, json=json, params=params, headers=headers
                )
            except httpx.TimeoutException as e:
                self._breaker.record_failure()
                last_exc = FincodeTimeoutError(str(e))
            except httpx.HTTPError as e:
                # 接続失敗などの transport エラーは一時的失敗。素の FincodeApiError に
                # すると呼び出し側（plan_service.fetch 等）が「4xx = 恒久エラー」として
                # 422 に誤翻訳してしまうため、503 系として区別する。
                self._breaker.record_failure()
                last_exc = FincodeServerError(str(e))
            else:
                status = response.status_code
                if 200 <= status < 300:
                    self._breaker.record_success()
                    if status == 204 or not response.content:
                        return {}
                    return cast(dict[str, Any], response.json())

                # fincode のエラーコード/メッセージだけをサーバ側ログに残し、原因を切り分け
                # 可能にする。生本文・ヘッダ・カード/トークン/JWT は出さない。``fincode_response``
                # は logging の伏字キーなので使わず、非センシティブなキー名で個別フィールドを出す。
                fincode_error_code, fincode_error_message = _extract_fincode_error(response)
                logger.warning(
                    "fincode_api_error",
                    method=method,
                    path=path,
                    status=status,
                    fincode_error_code=fincode_error_code,
                    fincode_error_message=fincode_error_message,
                )

                if status == 429:
                    retry_after_raw = response.headers.get("Retry-After")
                    retry_after = (
                        int(retry_after_raw)
                        if retry_after_raw and retry_after_raw.isdigit()
                        else None
                    )
                    # docs/architecture/error-handling.md の仕様通り、429 はブレーカーを反転させない。
                    raise FincodeRateLimitError(retry_after=retry_after)

                if 400 <= status < 500:
                    raise FincodeApiError(f"fincode returned HTTP {status}")

                self._breaker.record_failure()
                last_exc = FincodeServerError(f"fincode returned HTTP {status}")

            if attempt < self._max_retries:
                await asyncio.sleep(0.2 * (2**attempt))

        assert last_exc is not None
        raise last_exc
