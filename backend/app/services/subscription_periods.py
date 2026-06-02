from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription

FINCODE_TIMEZONE = ZoneInfo("Asia/Tokyo")
PERIOD_END_KEYS = ("current_period_end", "next_charge_date", "stop_date")
FINCODE_DATETIME_FORMATS = (
    "%Y/%m/%d %H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_fincode_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return as_utc(value)
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    with suppress(ValueError):
        return as_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))

    for fmt in FINCODE_DATETIME_FORMATS:
        with suppress(ValueError):
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=FINCODE_TIMEZONE).astimezone(UTC)

    return None


def extract_current_period_end(raw: dict[str, object]) -> datetime | None:
    for key in PERIOD_END_KEYS:
        parsed = parse_fincode_datetime(raw.get(key))
        if parsed is not None:
            return parsed
    return None


def apply_current_period_end(sub: Subscription, raw: dict[str, object]) -> bool:
    period_end = extract_current_period_end(raw)
    if period_end is None:
        return False
    sub.current_period_end = period_end
    return True


def has_future_period(sub: Subscription, now: datetime | None = None) -> bool:
    if sub.current_period_end is None:
        return False
    return as_utc(sub.current_period_end) > (now or datetime.now(UTC))


def cancel_at_period_end(sub: Subscription, now: datetime | None = None) -> bool:
    return (
        sub.status == SubscriptionStatus.ACTIVE
        and sub.cancelled_at is not None
        and has_future_period(sub, now)
    )


def usable_subscription_conditions(now: datetime) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    return (
        Subscription.status == SubscriptionStatus.ACTIVE,
        or_(Subscription.cancelled_at.is_(None), Subscription.current_period_end > now),
    )
