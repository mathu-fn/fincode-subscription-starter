"""fincode サブスクリプションサービス。

サブスク作成・解約の薄いラッパー。作成の Idempotency-Key は呼び出し元が管理する
ノンス（クライアント提供の Idempotency-Key または生成 UUID）から決定論的に生成し、
リトライ全体で同じキーを再利用する。解約（DELETE）は本質的に冪等なのでキー不要。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.fincode.base import FINCODE_TIMEZONE, BaseFincodeService
from app.services.fincode.idempotency import idem_key


class FincodeSubscriptionService(BaseFincodeService):
    async def create(
        self,
        *,
        user_id: int,
        customer_id: str,
        card_id: str,
        plan_id: str,
        nonce: str,
    ) -> dict[str, Any]:
        # fincode の日付境界は JST。UTC で日付を作ると JST 0:00〜8:59 に前日を
        # 送ってしまい、過去日の start_date として拒否される。
        start_date = datetime.now(FINCODE_TIMEZONE).strftime("%Y/%m/%d")
        return await self._client.request(
            "POST",
            "/v1/subscriptions",
            json={
                "pay_type": "Card",
                "customer_id": customer_id,
                "card_id": card_id,
                "plan_id": plan_id,
                "start_date": start_date,
            },
            idempotency_key=idem_key("sub.create", user_id, nonce),
        )

    async def cancel(self, *, fincode_subscription_id: str) -> dict[str, Any]:
        # fincode の解約は ``DELETE /v1/subscriptions/{id}``。将来の課金を停止し、
        # サブスクの ``status`` を ``CANCELED`` にする（ネイティブな期間末解約も
        # 日割りも無い）。支払い済み期限は登録時の ``next_charge_date`` 由来で確定済みなので、
        # 「期間末まで利用可」はアプリ側ポリシー。解約レスポンスでこの期限を縮めない
        # （``subscription_periods.apply_current_period_end(..., only_extend=True)``）。
        # ``pay_type`` はクエリパラメータで渡す（fincode 公式 SDK の cancel と同じ。ボディには
        # 入れない）。これが無いと fincode は 400 を返す。
        return await self._client.request(
            "DELETE",
            f"/v1/subscriptions/{fincode_subscription_id}",
            params={"pay_type": "Card"},
        )
