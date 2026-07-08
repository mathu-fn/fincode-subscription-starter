"""ローカルユーザーに対応する fincode 顧客行を検索または作成する。

fincode 顧客 ID は遅延作成される — 初回のカード登録または契約時に生成される。
行が存在すれば以降は同じレコードを再利用し、このシステムの他の部分が顧客を作成することはない。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CircuitBreakerOpenError,
    FincodeApiError,
    FincodeRateLimitError,
    FincodeServerError,
    FincodeTimeoutError,
)
from app.models.fincode_customer import FincodeCustomer
from app.models.user import User
from app.services.fincode.client import FincodeClient
from app.services.fincode.customer_service import FincodeCustomerService


class CustomerSyncService:
    def __init__(self, client: FincodeClient) -> None:
        self._fincode = FincodeCustomerService(client)

    async def ensure(self, db: AsyncSession, user: User) -> FincodeCustomer:
        existing = await db.scalar(
            select(FincodeCustomer).where(FincodeCustomer.user_id == user.id)
        )
        if existing is not None:
            return existing

        # 前回の試行で fincode 側の顧客は作成されたがローカル行がロールバックされた場合、
        # 再 POST すると 4xx「顧客が既に存在する」が返る。その場合は決定論的 ID を再利用する。
        #
        # 一時的な失敗（5xx / タイムアウト / レート制限 / サーキットオープン）は
        # プレースホルダーへフォールスルーしてはいけない — fincode に顧客が存在するかどうか
        # 不明であり、``local_user_{id}`` というフェイク値を永続化してしまうとキャッシュが
        # 永久に汚染される（以降のカード・契約呼び出しが fincode に存在しない顧客を参照する）。
        # 呼び出し元が正常に失敗しユーザーが再試行できるよう、例外を再送出する。
        try:
            created = await self._fincode.create(user_id=user.id, email=user.email, name=user.name)
            customer_id = created.get("id") or f"local_user_{user.id}"
        except (
            FincodeServerError,
            FincodeTimeoutError,
            FincodeRateLimitError,
            CircuitBreakerOpenError,
        ):
            raise
        except FincodeApiError:
            customer_id = f"local_user_{user.id}"

        # rollback はセッション内の全オブジェクトを expire するため、以降の属性アクセスが
        # 暗黙 IO にならないよう ID を先に退避しておく。
        user_id = user.id
        customer = FincodeCustomer(
            user_id=user_id,
            fincode_customer_id=customer_id,
        )
        db.add(customer)
        try:
            await db.flush()
        except IntegrityError:
            # 事前 SELECT を通り抜けた並行 INSERT（TOCTOU）。fincode_customers.user_id は
            # unique なので、勝った側の行を読み直して返す。fincode 側は決定論的な顧客 ID +
            # 固定 Idempotency-Key のため二重作成にはならない。
            await db.rollback()
            winner: FincodeCustomer | None = await db.scalar(
                select(FincodeCustomer).where(FincodeCustomer.user_id == user_id)
            )
            if winner is None:
                raise
            return winner
        return customer
