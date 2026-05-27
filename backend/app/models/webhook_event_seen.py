from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WebhookEventSeen(Base):
    __tablename__ = "webhook_events_seen"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fincode_event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dlq_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
