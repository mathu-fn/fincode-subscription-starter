from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.services.fincode.base import FINCODE_TIMEZONE

# fincode のサブスクオブジェクトに ``current_period_end`` は存在しない（公式 SDK
# fincode-sdk-node の型定義で確認）。支払い済み期限は ``next_charge_date``（次回課金日）で
# 表現される。``stop_date`` は「解約発効日」であって支払い済み期限ではないため、
# 期間末のソースには含めない（含めると解約レスポンスが期限を縮めてしまう）。
PERIOD_END_KEYS = ("current_period_end", "next_charge_date")
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


def apply_current_period_end(
    sub: Subscription, raw: dict[str, object], *, only_extend: bool = False
) -> bool:
    period_end = extract_current_period_end(raw)
    if period_end is None:
        return False
    # 解約系パス（``only_extend=True``）では、レスポンスが期限を「縮める」ことを禁じる。
    # 支払い済み期限は subscribe / change_plan 時点で確定済みであり、解約はそれを
    # 失効させる方向にしか作用しない（期限自体を前倒ししてはならない）。
    if (
        only_extend
        and sub.current_period_end is not None
        and period_end <= as_utc(sub.current_period_end)
    ):
        return False
    sub.current_period_end = period_end
    return True


def has_future_period(sub: Subscription, now: datetime | None = None) -> bool:
    if sub.current_period_end is None:
        return False
    return as_utc(sub.current_period_end) > (now or datetime.now(UTC))


def cancel_at_period_end(sub: Subscription) -> bool:
    # 判定の正本は model の ``Subscription.cancel_at_period_end`` property
    # （``SubscriptionOut`` スキーマ＝API レスポンスもこれを使う）。ここはそれに委譲して
    # 二重実装を避ける。逆方向（model→service）の参照は循環参照になるため採らない。
    return sub.cancel_at_period_end


def usable_subscription_conditions(now: datetime) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    return (
        Subscription.status == SubscriptionStatus.ACTIVE,
        or_(Subscription.cancelled_at.is_(None), Subscription.current_period_end > now),
    )
