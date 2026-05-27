"""シークレット情報を削除する構造化ログ。

リダクト用プロセッサーがレンダリング前にシークレットや PII を含む可能性のある
キーをログイベント辞書から取り除く。生の fincode レスポンス・JWT・パスワード・
トークン・カード情報はログに記録してはいけない。
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "card",
    "card_number",
    "pan",
    "cvc",
    "fincode_signature",
    "x-api-key",
    "api_key",
    "fincode_response",
    "secret",
}


def _redact(_: Any, __: str, event_dict: dict) -> dict:
    def scrub(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: ("***" if k.lower() in _SENSITIVE_KEYS else scrub(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(event_dict)


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
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
