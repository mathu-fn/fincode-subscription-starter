"""fincode クライアント用の小さなサーキットブレーカー。

状態:
- ``closed`` — リクエストは通過する。連続失敗でカウンターが増加する。
- ``open`` — リクエストは ``CircuitBreakerOpenError`` で即時失敗する。
- ``half_open`` — ``recovery_seconds`` 経過後、次のリクエストをプローブとして使用する。
  その結果に基づいてクローズまたは再オープンする。

5xx・タイムアウト・接続失敗のみが失敗としてカウントされる。
HTTP 4xx と 429 はブレーカーを反転させない。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.core.exceptions import CircuitBreakerOpenError


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_seconds: float = 30.0

    _failures: int = 0
    _state: str = "closed"  # closed | open | half_open
    _opened_at: float = 0.0

    def before_call(self) -> None:
        if self._state == "open":
            if (time.monotonic() - self._opened_at) >= self.recovery_seconds:
                self._state = "half_open"
            else:
                raise CircuitBreakerOpenError()

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold or self._state == "half_open":
            self._state = "open"
            self._opened_at = time.monotonic()

    @property
    def state(self) -> str:
        return self._state
