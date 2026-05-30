"""ドメインのステータス値を一箇所に集約する列挙。

``StrEnum`` なので各メンバーは ``str`` のサブクラスであり、SQLAlchemy の
``String`` カラム・クエリ比較・JSONB 監査ペイロードにそのまま渡しても
プレーンな文字列として扱われる（``SubscriptionStatus.ACTIVE == "active"``）。
これにより DB に保存される値や API レスポンスは一切変わらない。
"""

from __future__ import annotations

from enum import StrEnum


class SubscriptionStatus(StrEnum):
    """``subscriptions.status`` がとり得る値。"""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"


class PaymentStatus(StrEnum):
    """``subscription_results.status`` としてこのアプリが生成する値。

    fincode が送ってくる任意の ``status`` 文字列はそのまま保存されるため、
    ここに列挙するのは Webhook ハンドラーが自前で導出する代表値のみ。
    """

    SUCCEEDED = "succeeded"
    FAILED = "failed"
