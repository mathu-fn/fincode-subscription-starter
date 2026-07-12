"""fincode 顧客エンドポイントのラッパー。

このサービスはローカル DB を直接操作しない。fincode の JSON を
ドメインサービスが使用するプレーンな Python 辞書に変換する。
"""

from __future__ import annotations

from typing import Any

from app.services.fincode.base import BaseFincodeService
from app.services.fincode.idempotency import idem_key


def local_customer_id(user_id: int) -> str:
    """ローカルユーザーから決定論的に導出する fincode 顧客 ID。

    作成リクエストの ``id`` と、fincode 応答が使えない場合のフォールバックの両方が
    この 1 箇所から導出される（書式がずれると顧客の対応付けが壊れる）。
    """
    return f"local_user_{user_id}"


class FincodeCustomerService(BaseFincodeService):
    async def create(self, *, user_id: int, email: str, name: str) -> dict[str, Any]:
        body = {"id": local_customer_id(user_id), "email": email, "name": name}
        return await self._client.request(
            "POST",
            "/v1/customers",
            json=body,
            idempotency_key=idem_key("customer.create", user_id),
        )
