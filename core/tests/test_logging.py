"""Structured JSON log records — seam S2."""

import io
import json
from datetime import UTC, datetime
from typing import Any

from core.logging import configure_logging, get_logger, request_context


def _emitted(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_a_log_line_is_one_json_object_with_severity_message_and_timestamp() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)

    get_logger(__name__).info("Session started")

    (record,) = _emitted(stream)
    assert record["severity"] == "INFO"
    assert record["message"] == "Session started"
    assert datetime.fromisoformat(record["timestamp"]).tzinfo == UTC


def test_severity_uses_cloud_logging_names() -> None:
    stream = io.StringIO()
    configure_logging(level="DEBUG", stream=stream)
    logger = get_logger(__name__)

    logger.debug("looking up the KB Section")
    logger.warning("no Strategist online")
    logger.error("provider refused the Turn")

    assert [record["severity"] for record in _emitted(stream)] == ["DEBUG", "WARNING", "ERROR"]


def test_the_request_id_is_carried_by_every_line_inside_the_request() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)

    with request_context(request_id="req-0100"):
        get_logger(__name__).info("Turn received")

    (record,) = _emitted(stream)
    assert record["request_id"] == "req-0100"


def test_the_session_id_is_included_when_known_and_absent_when_not() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    logger = get_logger(__name__)

    with request_context(request_id="req-0100"):
        logger.info("Session unknown so far")
        with request_context(request_id="req-0100", session_id="sess-0100"):
            logger.info("Turn stored")

    without_session, with_session = _emitted(stream)
    assert "session_id" not in without_session
    assert with_session["session_id"] == "sess-0100"


def test_the_request_context_is_cleared_when_the_request_ends() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    logger = get_logger(__name__)

    with request_context(request_id="req-0100"):
        logger.info("inside")
    logger.info("outside")

    _inside, outside = _emitted(stream)
    assert "request_id" not in outside


def test_debug_lines_are_emitted_only_when_the_level_is_debug() -> None:
    quiet = io.StringIO()
    configure_logging(level="INFO", stream=quiet)
    get_logger(__name__).debug("prompt assembled")
    assert _emitted(quiet) == []

    verbose = io.StringIO()
    configure_logging(level="DEBUG", stream=verbose)
    get_logger(__name__).debug("prompt assembled")
    assert [record["message"] for record in _emitted(verbose)] == ["prompt assembled"]
