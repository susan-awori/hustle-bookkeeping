"""Structured logging with an explicit allowlist.

Never log full transcripts, phone numbers, PINs, tokens, or ledger amounts
at INFO or above. Unknown keys are dropped or replaced with [REDACTED].
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

import structlog

ALLOWLIST = frozenset(
    {
        "event",
        "level",
        "timestamp",
        "logger",
        "entry_type",
        "trader_id_hash",
        "http_method",
        "http_path",
        "status_code",
        "duration_ms",
        "error_class",
        "save_voice_notes",
        "entry_count",
        "expired_count",
        "environment",
    }
)

SENSITIVE_KEY_FRAGMENTS = (
    "phone",
    "pin",
    "password",
    "secret",
    "token",
    "transcript",
    "amount",
    "audio",
    "authorization",
    "counterparty",
    "description",
    "display_name",
    "raw_",
    "kes",
)


def hash_trader_id(trader_id: str, pepper: str) -> str:
    digest = hmac.new(pepper.encode("utf-8"), str(trader_id).encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:16]


def _looks_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def redact_event_dict(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in event_dict.items():
        if key in ALLOWLIST:
            cleaned[key] = value
        elif _looks_sensitive(str(key)):
            cleaned[key] = "[REDACTED]"
        else:
            # Drop unknown fields rather than risk leaking user data.
            continue
    if "timestamp" not in cleaned:
        cleaned["timestamp"] = datetime.now(timezone.utc).isoformat()
    return cleaned


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            redact_event_dict,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()
