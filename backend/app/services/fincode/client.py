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
from typing import Any, Protocol

import httpx

from app.core.exceptions import (
    FincodeApiError,
    FincodeRateLimitError,
    FincodeServerError,
    FincodeTimeoutError,
)
from app.services.fincode.circuit_breaker import CircuitBreaker


class FincodeClient(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...


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
        json: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            self._breaker.before_call()

            try:
                response = await self._client.request(method, path, json=json, headers=headers)
            except httpx.TimeoutException as e:
                self._breaker.record_failure()
                last_exc = FincodeTimeoutError(str(e))
            except httpx.HTTPError as e:
                self._breaker.record_failure()
                last_exc = FincodeApiError(str(e))
            else:
                status = response.status_code
                if 200 <= status < 300:
                    self._breaker.record_success()
                    if status == 204 or not response.content:
                        return {}
                    return response.json()

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
