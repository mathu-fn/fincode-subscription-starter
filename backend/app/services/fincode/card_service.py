from __future__ import annotations

from app.services.fincode.client import FincodeClient
from app.services.fincode.idempotency import idem_key, token_fingerprint


class FincodeCardService:
    def __init__(self, client: FincodeClient) -> None:
        self._client = client

    async def create(self, *, user_id: int, customer_id: str, token: str, default_flag: str = "0") -> dict:
        return await self._client.request(
            "POST",
            f"/v1/customers/{customer_id}/cards",
            json={"token": token, "default_flag": default_flag},
            idempotency_key=idem_key("card.create", user_id, token_fingerprint(token)),
        )

    async def delete(self, *, customer_id: str, card_id: str) -> dict:
        return await self._client.request(
            "DELETE",
            f"/v1/customers/{customer_id}/cards/{card_id}",
        )
