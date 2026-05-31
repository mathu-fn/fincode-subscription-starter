from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.audit_logger import AuditLogger
from app.services.customer_sync_service import CustomerSyncService
from app.services.fincode.client import FincodeClient


class BaseManager(ABC):
    """Manager 共通の依存（fincode クライアント・監査・顧客同期）を保持する抽象基底。"""

    def __init__(self, client: FincodeClient, audit: AuditLogger | None = None) -> None:
        self._client = client
        self._audit = audit or AuditLogger()
        self._customers = CustomerSyncService(client)

    @property
    @abstractmethod
    def auditable_type(self) -> str:
        """この Manager が監査ログへ記録するリソース種別。サブクラスが定義する。"""
