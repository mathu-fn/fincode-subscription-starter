"""fincode 顧客エンドポイントのラッパー。

このサービスはローカル DB を直接操作しない。fincode の JSON を
ドメインサービスが使用するプレーンな Python 辞書に変換する。
"""

from __future__ import annotations

from app.services.fincode.base import BaseFincodeService
from app.services.fincode.idempotency import idem_key


class FincodeCustomerService(BaseFincodeService):
    async def create(self, *, user_id: int, email: str, name: str) -> dict:
        body = {"id": f"local_user_{user_id}", "email": email, "name": name}
        return await self._client.request(
            "POST",
            "/v1/customers",
            json=body,
            idempotency_key=idem_key("customer.create", user_id),
        )
