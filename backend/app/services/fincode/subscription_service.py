from __future__ import annotations

from datetime import datetime, timezone

from app.services.fincode.base import BaseFincodeService
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
    ) -> dict:
        start_date = datetime.now(timezone.utc).strftime("%Y/%m/%d")
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

    async def cancel(self, *, fincode_subscription_id: str) -> dict:
        return await self._client.request(
            "PUT",
            f"/v1/subscriptions/{fincode_subscription_id}/cancel",
        )
