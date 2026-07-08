"""シークレット情報を削除する構造化ログ。

リダクト用プロセッサーがレンダリング前にシークレットや PII を含む可能性のある
キーをログイベント辞書から取り除く。生の fincode レスポンス・JWT・パスワード・
トークン・カード情報はログに記録してはいけない。
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, cast

import structlog
from structlog.typing import FilteringBoundLogger

from app.core.redaction import scrub


def _redact(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> Mapping[str, Any]:
    scrubbed = scrub(dict(event_dict))
    if isinstance(scrubbed, Mapping):
        return scrubbed
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # logger.exception の exc_info をトレースバック文字列へ整形する。
            # _redact より前に置き、整形後のイベント辞書にもリダクトを効かせる。
            structlog.processors.format_exc_info,
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    return cast(FilteringBoundLogger, structlog.get_logger(name))
