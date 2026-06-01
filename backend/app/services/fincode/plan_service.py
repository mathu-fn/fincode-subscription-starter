"""小さなインメモリ TTL キャッシュを持つ fincode プランサービス。

プランの正本は fincode 側にある。キャッシュは ``GET /api/subscription/plans`` の
レイテンシを削減するが、プラン編集が素早く反映されるよう TTL は短く（60秒）保つ。
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from app.core.exceptions import UnprocessableError
from app.services.fincode.base import BaseFincodeService
from app.services.fincode.client import FincodeClient


class PlanData(TypedDict):
    """``_normalise`` が返す、fincode プランの正規化済み内部表現。

    fincode の生レスポンス（``raw``）と、UI / 契約スナップショットが参照する
    フラットなフィールドを併せ持つ。``raw`` は ``subscriptions.plan_snapshot``
    に凍結保存される。
    """

    fincode_plan_id: str
    name: str
    amount: int
    currency: str
    interval: str
    raw: dict[str, Any]


class FincodePlanService(BaseFincodeService):
    _cache_ttl = 60.0

    def __init__(self, client: FincodeClient) -> None:
        super().__init__(client)
        self._list_cache: tuple[float, list[PlanData]] | None = None
        self._plan_cache: dict[str, tuple[float, PlanData]] = {}

    @staticmethod
    def _is_active(raw: dict[str, Any]) -> bool:
        # fincode は削除済みプランを delete_flag="1"（文字列）でマークする。
        # それ以外の値（フィールド自体が存在しない場合も含む）は利用可能として扱う。
        return str(raw.get("delete_flag", "0")) != "1"

    @staticmethod
    def _normalise(raw: dict[str, Any]) -> PlanData:
        amount = raw.get("amount", "0")
        try:
            amount_int = int(amount)
        except (TypeError, ValueError):
            amount_int = 0
        return {
            "fincode_plan_id": raw.get("id", ""),
            "name": raw.get("plan_name") or raw.get("name") or "",
            "amount": amount_int,
            "currency": raw.get("currency", "JPY"),
            "interval": raw.get("interval_pattern") or raw.get("interval") or "month",
            "raw": raw,
        }

    async def list_active(self) -> list[PlanData]:
        now = time.monotonic()
        if self._list_cache and (now - self._list_cache[0]) < self._cache_ttl:
            return self._list_cache[1]
        response = await self._client.request("GET", "/v1/plans")
        items = response.get("list", [])
        result = [
            self._normalise(item)
            for item in items
            if isinstance(item, dict) and self._is_active(item)
        ]
        self._list_cache = (now, result)
        return result

    async def fetch(self, plan_id: str) -> PlanData:
        now = time.monotonic()
        cached = self._plan_cache.get(plan_id)
        if cached and (now - cached[0]) < self._cache_ttl:
            return cached[1]
        try:
            raw = await self._client.request("GET", f"/v1/plans/{plan_id}")
        except Exception as e:
            raise UnprocessableError(f"Plan {plan_id} is not available.", code="plan_unavailable") from e
        if not self._is_active(raw):
            raise UnprocessableError(f"Plan {plan_id} is not active.", code="plan_unavailable")
        normalised = self._normalise(raw)
        self._plan_cache[plan_id] = (now, normalised)
        return normalised

    def invalidate(self) -> None:
        self._list_cache = None
        self._plan_cache.clear()
