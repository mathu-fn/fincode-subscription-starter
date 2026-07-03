from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SubscriptionStatus
from app.models.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    # フリープラン（0円・ローカル完結）はカード/顧客を持たないため NULL 許容。
    fincode_customer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("fincode_customers.id"), nullable=True
    )
    fincode_card_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("fincode_cards.id"), nullable=True
    )
    fincode_subscription_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    fincode_plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_interval: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=SubscriptionStatus.ACTIVE, nullable=False, index=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def cancel_at_period_end(self) -> bool:
        # current_period_end は DateTime(timezone=True) カラムで、書き込みも
        # 常に tz-aware UTC（subscription_periods.apply_current_period_end）。
        period_end = self.current_period_end
        if (
            self.status != SubscriptionStatus.ACTIVE
            or self.cancelled_at is None
            or period_end is None
        ):
            return False
        return period_end > datetime.now(UTC)
