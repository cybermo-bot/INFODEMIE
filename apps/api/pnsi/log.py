"""Structured JSON logging with secret redaction (CLAUDE.md rule 10).

Two layers of protection:
1. Any field whose name looks sensitive (password, token, secret, key, cookie,
   authorization) is masked whatever its value.
2. Any configured secret value is masked wherever it appears in a log line,
   including inside free text and exception messages.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

import structlog

MASK = "***"
SENSITIVE_KEY = re.compile(
    r"(pass(word)?|secret|token|api[_-]?key|authorization|cookie|csrf|session|credential)",
    re.IGNORECASE,
)


class SecretRedactor:
    """structlog processor that masks sensitive fields and known secret values."""

    def __init__(self, secret_values: Iterable[str] = ()) -> None:
        # Longest first so a secret that contains another is fully masked.
        self._secrets = sorted({s for s in secret_values if len(s) >= 4}, key=len, reverse=True)

    def _scrub_text(self, text: str) -> str:
        for secret in self._secrets:
            if secret in text:
                text = text.replace(secret, MASK)
        return text

    def scrub(self, value: Any, key: str | None = None) -> Any:
        if key is not None and SENSITIVE_KEY.search(key):
            return MASK
        if isinstance(value, str):
            return self._scrub_text(value)
        if isinstance(value, Mapping):
            return {k: self.scrub(v, str(k)) for k, v in value.items()}
        if isinstance(value, list | tuple | set):
            return [self.scrub(v) for v in value]
        return value

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            k: (self.scrub(v) if k in ("event", "exception") else self.scrub(v, k))
            for k, v in event_dict.items()
        }


def configure_logging(level: str = "INFO", secret_values: Iterable[str] = ()) -> None:
    redactor = SecretRedactor(secret_values)
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            redactor,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "celery"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
