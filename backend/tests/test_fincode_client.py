"""Unit tests for FincodeHttpClient and CircuitBreaker."""

from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import (
    CircuitBreakerOpenError,
    FincodeApiError,
    FincodeRateLimitError,
    FincodeServerError,
    FincodeTimeoutError,
)
from app.services.fincode.circuit_breaker import CircuitBreaker
from app.services.fincode.client import FincodeHttpClient

pytestmark = pytest.mark.asyncio


def make_client(handler, *, breaker: CircuitBreaker | None = None) -> FincodeHttpClient:
    transport = httpx.MockTransport(handler)
    return FincodeHttpClient(
        base_url="https://api.test.fincode.jp",
        api_key="m_test_dummy",
        max_retries=2,
        breaker=breaker or CircuitBreaker(failure_threshold=3, recovery_seconds=0.05),
        transport=transport,
    )


async def test_post_returns_json_and_sends_idempotency_key() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["idem"] = request.headers.get("Idempotency-Key", "")
        captured["auth"] = request.headers.get("Authorization", "")
        return httpx.Response(200, json={"id": "cus_1"})

    client = make_client(handler)
    try:
        result = await client.request(
            "POST", "/v1/customers", json={"name": "x"}, idempotency_key="key-1"
        )
        assert result == {"id": "cus_1"}
        assert captured["idem"] == "key-1"
        assert captured["auth"] == "Bearer m_test_dummy"
    finally:
        await client.aclose()


async def test_retries_on_500_then_succeeds() -> None:
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        if counter["n"] < 3:
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    try:
        result = await client.request("POST", "/v1/customers", json={})
        assert result == {"ok": True}
        assert counter["n"] == 3
    finally:
        await client.aclose()


async def test_5xx_after_retries_raises_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    client = make_client(handler)
    try:
        with pytest.raises(FincodeServerError):
            await client.request("POST", "/v1/customers", json={})
    finally:
        await client.aclose()


async def test_429_raises_rate_limit_immediately() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "30"}, json={"error": "slow"})

    client = make_client(handler)
    try:
        with pytest.raises(FincodeRateLimitError) as exc_info:
            await client.request("POST", "/v1/customers", json={})
        assert exc_info.value.retry_after == 30
        # 429 is not retried.
        assert calls["n"] == 1
    finally:
        await client.aclose()


async def test_4xx_raises_api_error_without_retry() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    client = make_client(handler)
    try:
        with pytest.raises(FincodeApiError):
            await client.request("POST", "/v1/customers", json={})
        assert calls["n"] == 1
    finally:
        await client.aclose()


async def test_connect_error_retries_then_raises_server_error() -> None:
    # 接続失敗は一時的失敗。素の FincodeApiError（4xx 相当＝恒久扱い）にすると
    # plan_service.fetch が 422 plan_unavailable へ誤翻訳するため、503 系で raise する。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("connection refused")

    client = make_client(handler)
    try:
        with pytest.raises(FincodeServerError):
            await client.request("GET", "/v1/plans")
        assert calls["n"] == 3  # initial + 2 retries
    finally:
        await client.aclose()


async def test_timeout_retries_then_raises() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.TimeoutException("slow")

    client = make_client(handler)
    try:
        with pytest.raises(FincodeTimeoutError):
            await client.request("POST", "/v1/customers", json={})
        assert calls["n"] == 3  # initial + 2 retries
    finally:
        await client.aclose()


async def test_circuit_breaker_opens_after_threshold() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "x"})

    breaker = CircuitBreaker(failure_threshold=3, recovery_seconds=60.0)
    client = make_client(handler, breaker=breaker)
    try:
        # First call: 3 retries × 500 = 3 failures recorded -> breaker opens
        with pytest.raises(FincodeServerError):
            await client.request("POST", "/v1/customers", json={})
        assert breaker.state == "open"

        # Second call: fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await client.request("POST", "/v1/customers", json={})
    finally:
        await client.aclose()
