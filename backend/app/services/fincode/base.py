from __future__ import annotations

from app.services.fincode.client import FincodeClient


class BaseFincodeService:
    """fincode エンドポイントラッパー共通の基底。クライアントを保持する。"""

    def __init__(self, client: FincodeClient) -> None:
        self._client = client
