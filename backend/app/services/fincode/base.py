from __future__ import annotations

from zoneinfo import ZoneInfo

from app.services.fincode.client import FincodeClient

# fincode は日本のサービスであり、日付境界（start_date や課金日）は JST で解釈される。
FINCODE_TIMEZONE = ZoneInfo("Asia/Tokyo")


class BaseFincodeService:
    """fincode エンドポイントラッパー共通の基底。クライアントを保持する。"""

    def __init__(self, client: FincodeClient) -> None:
        self._client = client
