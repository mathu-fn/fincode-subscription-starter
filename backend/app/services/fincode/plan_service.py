"""小さなインメモリ TTL キャッシュを持つ fincode プランサービス。

プランの正本は fincode 側にある。キャッシュは ``GET /api/subscription/plans`` の
レイテンシを削減するが、プラン編集が素早く反映されるよう TTL は短く（60秒）保つ。
"""

from __future__ import annotations

import time

from app.core.exceptions import PlanUnavailableError
from app.services.fincode.client import FincodeClient


class FincodePlanService:
    _cache_ttl = 60.0

    def __init__(self, client: FincodeClient) -> None:
        self._client = client
        self._list_cache: tuple[float, list[dict]] | None = None
        self._plan_cache: dict[str, tuple[float, dict]] = {}

    @staticmethod
    def _is_active(raw: dict) -> bool:
        # fincode は削除済みプランを delete_flag="1"（文字列）でマークする。
        # それ以外の値（フィールド自体が存在しない場合も含む）は利用可能として扱う。
        return str(raw.get("delete_flag", "0")) != "1"

    @staticmethod
    def _normalise(raw: dict) -> dict:
        amount = raw.get("amount", "0")
        try:
            amount_int = int(amount)
        except (TypeError, ValueError):
            amount_int = 0
        return {
            "fincode_plan_id": raw.get("id"),
            "name": raw.get("plan_name") or raw.get("name") or "",
            "amount": amount_int,
            "currency": raw.get("currency", "JPY"),
            "interval": raw.get("interval_pattern") or raw.get("interval") or "month",
            "raw": raw,
        }

    async def list_active(self) -> list[dict]:
        now = time.monotonic()
        if self._list_cache and (now - self._list_cache[0]) < self._cache_ttl:
            return self._list_cache[1]
        response = await self._client.request("GET", "/v1/plans")
        items = response.get("list", []) if isinstance(response, dict) else []
        result = [self._normalise(item) for item in items if self._is_active(item)]
        self._list_cache = (now, result)
        return result

    async def fetch(self, plan_id: str) -> dict:
        now = time.monotonic()
        cached = self._plan_cache.get(plan_id)
        if cached and (now - cached[0]) < self._cache_ttl:
            return cached[1]
        try:
            raw = await self._client.request("GET", f"/v1/plans/{plan_id}")
        except Exception as e:
            raise PlanUnavailableError(f"Plan {plan_id} is not available.") from e
        if not self._is_active(raw):
            raise PlanUnavailableError(f"Plan {plan_id} is not active.")
        normalised = self._normalise(raw)
        self._plan_cache[plan_id] = (now, normalised)
        return normalised

    def invalidate(self) -> None:
        self._list_cache = None
        self._plan_cache.clear()
