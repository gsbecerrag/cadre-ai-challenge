"""Structured JSON logging to stdout.

Every line is one JSON object carrying Cloud Logging's `severity`, the `message`, an ISO-8601
`timestamp`, and the correlation ids bound for the current request — so a log line, a Trace and
a Firestore document can be joined. `print` is forbidden anywhere in the codebase (ruff T20).
"""

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, TextIO

from core.config import LogLevel

_ROOT_LOGGER_NAME = "cadre"

# Correlation ids for the request being served, bound by the API middleware.
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)

# Keys the stdlib puts on every LogRecord; anything else passed through `extra` is ours.
_STANDARD_RECORD_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
        }
        request_id = getattr(record, "request_id", None) or _request_id.get()
        if request_id:
            payload["request_id"] = request_id
        session_id = getattr(record, "session_id", None) or _session_id.get()
        if session_id:
            payload["session_id"] = session_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_KEYS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: LogLevel = "INFO", stream: TextIO | None = None) -> None:
    """Point the application logger at one JSON stream handler. Safe to call again."""
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """A logger under the application root, so every line goes through the JSON handler."""
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


@contextmanager
def request_context(request_id: str, session_id: str | None = None) -> Iterator[None]:
    """Bind correlation ids for the duration of one request, then restore what was there."""
    request_token = _request_id.set(request_id)
    session_token = _session_id.set(session_id)
    try:
        yield
    finally:
        _session_id.reset(session_token)
        _request_id.reset(request_token)
