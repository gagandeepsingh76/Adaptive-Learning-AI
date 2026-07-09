"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog

from app.config.settings import Settings

_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "openrouter_api_key",
        "api_key",
        "prompt",
        "question",
        "content",
        "vector",
        "embedding",
    }
)


def _redact_sensitive_values(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Remove known sensitive values before any renderer sees the event."""
    for key in tuple(event_dict):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure standard-library and structlog output as JSON events."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_sensitive_values,
    ]
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to a component name."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name).bind(component=name))
