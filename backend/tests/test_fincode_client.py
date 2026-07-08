"""Unit tests for FincodeHttpClient and CircuitBreaker."""

from __future__ import annotations

import asyncio

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

    breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=60.0)
    client = make_client(handler, breaker=breaker)
    try:
        with pytest.raises(FincodeRateLimitError) as exc_info:
            await client.request("POST", "/v1/customers", json={})
        assert exc_info.value.retry_after == 30
        # 429 is not retried, and does not trip the breaker.
        assert calls["n"] == 1
        assert breaker.state == "closed"
    finally:
        await client.aclose()


async def test_4xx_raises_api_error_without_retry() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=60.0)
    client = make_client(handler, breaker=breaker)
    try:
        with pytest.raises(FincodeApiError):
            await client.request("POST", "/v1/customers", json={})
        assert calls["n"] == 1
        # 4xx does not trip the breaker either.
        assert breaker.state == "closed"
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


async def test_circuit_breaker_closes_after_successful_probe() -> None:
    # open → recovery_seconds 経過 → half_open プローブ成功 → closed。
    responses = {"status": 500}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(responses["status"], json={})

    breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
    client = make_client(handler, breaker=breaker)
    try:
        with pytest.raises(FincodeServerError):
            await client.request("POST", "/v1/customers", json={})
        assert breaker.state == "open"

        await asyncio.sleep(0.06)
        responses["status"] = 200
        result = await client.request("POST", "/v1/customers", json={})
        assert result == {}
        assert breaker.state == "closed"
    finally:
        await client.aclose()


async def test_circuit_breaker_reopens_on_failed_probe() -> None:
    # half_open 中の失敗は閾値に関係なく即座に open へ戻る。
    breaker = CircuitBreaker(failure_threshold=5, recovery_seconds=0.05)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    client = make_client(handler, breaker=breaker)
    try:
        # 閾値 5 に対しリトライ 3 回では open にならないので、直接 open にする。
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "open"

        await asyncio.sleep(0.06)
        # プローブ（初回試行）が 500 → record_failure が half_open を検知して即 open。
        with pytest.raises((FincodeServerError, CircuitBreakerOpenError)):
            await client.request("POST", "/v1/customers", json={})
        assert breaker.state == "open"
    finally:
        await client.aclose()
