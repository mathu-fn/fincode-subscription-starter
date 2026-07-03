"""fincode モッククライアント（``FINCODE_MODE=mock`` 用）。

fincode アカウントを用意しなくても UI / API を一通り触れるよう、実 HTTP の代わりに
固定のダミーデータを返す。``FincodeClient`` プロトコルを満たすため、Manager / サービス
層は実クライアント（``FincodeHttpClient``）と区別なく利用でき、業務ロジックには一切
手を入れない。

本物の fincode API は決して叩かない。Idempotency-Key・リトライ・サーキットブレーカー
といった HTTP 周りの関心事はモックでは無関係なので、単純にパスとメソッドで分岐して
解析済み辞書を返すだけにしている。
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

# fincode 管理画面で作成したプランを模した「生レスポンス」。
# FincodePlanService._normalise が読むキー（id / plan_name / amount /
# currency / interval_pattern / delete_flag）に合わせている。
_MOCK_PLANS: dict[str, dict[str, Any]] = {
    "plan_mock_basic": {
        "id": "plan_mock_basic",
        "plan_name": "ベーシック(モック)",
        "amount": "500",
        "currency": "JPY",
        "interval_pattern": "month",
        "delete_flag": "0",
    },
    "plan_mock_pro": {
        "id": "plan_mock_pro",
        "plan_name": "プロ(モック)",
        "amount": "1500",
        "currency": "JPY",
        "interval_pattern": "month",
        "delete_flag": "0",
    },
}

_BRANDS = ("VISA", "Mastercard", "JCB", "AMEX")


def _digest(value: str) -> int:
    """入力文字列から決定論的な整数を作る。トークンごとに安定した値を返すため、
    同じカードトークンを再登録すると同じブランド・下4桁が表示される。"""
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


class FincodeMockClient:
    """``FincodeClient`` プロトコルのインメモリ実装。"""

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = json or {}

        # --- プラン -------------------------------------------------------
        if method == "GET" and path == "/v1/plans":
            return {"list": list(_MOCK_PLANS.values())}
        if method == "GET" and path.startswith("/v1/plans/"):
            plan_id = path.rsplit("/", 1)[-1]
            # 未知のプランIDでも契約フローを試せるよう、無ければ汎用プランを合成する。
            return _MOCK_PLANS.get(plan_id) or {
                "id": plan_id,
                "plan_name": "モックプラン",
                "amount": "1000",
                "currency": "JPY",
                "interval_pattern": "month",
                "delete_flag": "0",
            }

        # --- 顧客 ---------------------------------------------------------
        if method == "POST" and path == "/v1/customers":
            return {"id": body.get("id") or "customer_mock"}

        # --- カード -------------------------------------------------------
        if method == "POST" and "/customers/" in path and path.endswith("/cards"):
            d = _digest(body.get("token", "tok_mock"))
            return {
                "id": f"card_mock_{d % 1_000_000:06d}",
                "brand": _BRANDS[d % len(_BRANDS)],
                "card_no": f"************{d % 10000:04d}",
                "expire": "3012",  # YYMM = 2030/12（CardManager._parse_expire が解釈する）
                "default_flag": body.get("default_flag", "0"),
            }
        if method == "DELETE" and "/cards/" in path:
            return {}

        # --- 契約 ---------------------------------------------------------
        if method == "POST" and path == "/v1/subscriptions":
            d = _digest(idempotency_key or "sub_mock")
            period_end = datetime.now(UTC) + timedelta(days=30)
            return {
                "id": f"sub_mock_{d % 1_000_000:06d}",
                "status": "active",
                "current_period_end": period_end.isoformat(),
            }
        if method == "DELETE" and path.startswith("/v1/subscriptions/"):
            return {"status": "canceled"}

        # 想定外のパスはモックでは空の成功として握りつぶす。
        return {}

    async def aclose(self) -> None:
        """``FincodeHttpClient`` とのインターフェース互換。モックは何も保持しない。"""
        return None
