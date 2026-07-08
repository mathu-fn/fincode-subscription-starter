"""fincode クライアント用の小さなサーキットブレーカー。

状態:
- ``closed`` — リクエストは通過する。連続失敗でカウンターが増加する。
- ``open`` — リクエストは ``CircuitBreakerOpenError`` で即時失敗する。
- ``half_open`` — ``recovery_seconds`` 経過後に遷移し、リクエストをプローブとして
  通過させる。成功で ``closed``、失敗で即 ``open`` に戻る。プローブの結果が出る前に
  並行リクエストが到達した場合はそれらも通過する（プローブを 1 本に絞る排他は
  持たない。プローブが 4xx で終わると ``record_*`` が呼ばれず状態が固着するため、
  素通し方式のほうが安全側）。

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
