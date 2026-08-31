"""Structured JSON logging to stdout.

Every line is one JSON object carrying Cloud Logging's `severity`, the `message`, an ISO-8601
`timestamp`, and the correlation ids bound for the current request — so a log line, a Trace and
a Firestore document can be joined. `print` is forbidden anywhere in the codebase (ruff T20).

Bodies are redacted here rather than at each call site: every string a record carries — its
message, the fields passed through `extra`, the formatted exception — goes through the `full`
Redaction Profile on its way into the JSON object (ADR-0006). One place, so a line written by a
library, or by a call site added next month, cannot be the one that leaks. The correlation ids
are structure rather than body and are left alone: a request id is thirty-two hex characters,
which is also the shape of an API key, and redacting it would make a request's lines unjoinable.
"""

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, TextIO

from core import redaction
from core.config import LogLevel

_ROOT_LOGGER_NAME = "cadre"

# Uvicorn's startup and error lines go through its own loggers; they must be JSON too.
# The process root is managed as well, so a third-party library that logs (httpx, asyncio,
# a Google client) cannot emit a plain-text line that a log store is unable to query.
_MANAGED_LOGGER_NAMES = ("", _ROOT_LOGGER_NAME, "uvicorn", "uvicorn.error")

# The request middleware is the access log, with the request id and duration on it.
# Uvicorn's access log is plain text and would break the one-JSON-object-per-line contract.
_SILENCED_LOGGER_NAME = "uvicorn.access"

# Correlation ids for the request being served, bound by the API middleware.
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)

# Keys the stdlib puts on every LogRecord; anything else passed through `extra` is ours.
_STANDARD_RECORD_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
    # Uvicorn's ANSI-escaped copy of its own message — noise once the line is JSON.
    "color_message",
}


def redacted_body(text: str) -> str:
    """A log body, through the `full` Redaction Profile: the Refuse Set gone and Contact
    Details tokenised, because Cloud Logging is not a place Cadre keeps a Visitor's email."""
    return redaction.full(text).text


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object, with every body redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "severity": record.levelname,
            "message": redacted_body(record.getMessage()),
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "logger": record.name,
        }
        # Correlation ids are placed before the loop below, which is what keeps them out of
        # the redaction: they are structure, and a redacted request id joins nothing.
        request_id = getattr(record, "request_id", None) or _request_id.get()
        if request_id:
            payload["request_id"] = request_id
        session_id = getattr(record, "session_id", None) or _session_id.get()
        if session_id:
            payload["session_id"] = session_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_KEYS and key not in payload:
                payload[key] = redacted_body(value) if isinstance(value, str) else value
        if record.exc_info:
            payload["error"] = redacted_body(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


def _detach_handlers(logger: logging.Logger) -> None:
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)


def configure_logging(level: LogLevel = "INFO", stream: TextIO | None = None) -> None:
    """Point every logger the process uses at one JSON stream handler. Safe to call again."""
    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonFormatter())

    for name in _MANAGED_LOGGER_NAMES:
        logger = logging.getLogger(name)
        _detach_handlers(logger)
        logger.addHandler(handler)
        logger.setLevel(level)
        # Each managed logger owns the one handler, so a line is written exactly once.
        logger.propagate = False

    access_logger = logging.getLogger(_SILENCED_LOGGER_NAME)
    _detach_handlers(access_logger)
    access_logger.propagate = False
    access_logger.disabled = True


def get_logger(name: str) -> logging.Logger:
    """A logger under the application root, so every line goes through the JSON handler."""
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


@contextmanager
def session_context(session_id: str) -> Iterator[None]:
    """Bind the Session id for the rest of the request, once it is known — a Turn is streamed
    long after the middleware has bound the request id."""
    token = _session_id.set(session_id)
    try:
        yield
    finally:
        _session_id.reset(token)


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
