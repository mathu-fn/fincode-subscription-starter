"""fincode プランサービス。

プランの正本は fincode 側にある。キャッシュは持たず、プラン編集が即座に
反映されるよう毎回 fincode に問い合わせる。
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.core.exceptions import (
    CircuitBreakerOpenError,
    FincodeApiError,
    FincodeRateLimitError,
    FincodeServerError,
    FincodeTimeoutError,
    UnprocessableError,
)
from app.services.fincode.base import BaseFincodeService


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
        response = await self._client.request("GET", "/v1/plans")
        items = response.get("list", [])
        return [
            self._normalise(item)
            for item in items
            if isinstance(item, dict) and self._is_active(item)
        ]

    async def fetch(self, plan_id: str) -> PlanData:
        # 一時的な失敗（5xx / タイムアウト / レート制限 / サーキットオープン）を
        # ``plan_unavailable``（422）へ変換してはいけない — fincode 障害を「この
        # プランは利用できない」という恒久エラーとして見せてしまう。例外ハンドラが
        # 503/504/429 を返せるよう再送出し、4xx 相当の素の ``FincodeApiError``
        # （プランが存在しない等）だけを 422 に翻訳する。
        try:
            raw = await self._client.request("GET", f"/v1/plans/{plan_id}")
        except (
            FincodeServerError,
            FincodeTimeoutError,
            FincodeRateLimitError,
            CircuitBreakerOpenError,
        ):
            raise
        except FincodeApiError as e:
            raise UnprocessableError(
                f"Plan {plan_id} is not available.", code="plan_unavailable"
            ) from e
        if not self._is_active(raw):
            raise UnprocessableError(f"Plan {plan_id} is not active.", code="plan_unavailable")
        return self._normalise(raw)
