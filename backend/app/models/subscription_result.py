from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SubscriptionResult(Base):
    __tablename__ = "subscription_results"
    __table_args__ = (
        UniqueConstraint(
            "fincode_subscription_id",
            "fincode_payment_id",
            name="uq_subscription_results_sub_payment",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    fincode_subscription_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fincode_payment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    charged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fincode_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
