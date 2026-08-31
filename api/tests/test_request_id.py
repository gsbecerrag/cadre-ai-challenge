"""Request correlation — seam S1."""

from fastapi.testclient import TestClient

from api.tests.conftest import LogReader


def test_an_incoming_request_id_is_honoured_and_echoed(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-Id": "req-0100"})

    assert response.headers["x-request-id"] == "req-0100"


def test_a_request_id_is_assigned_when_the_caller_sends_none(client: TestClient) -> None:
    first = client.get("/healthz").headers["x-request-id"]
    second = client.get("/healthz").headers["x-request-id"]

    assert first and second and first != second


def test_the_request_is_logged_with_its_request_id(
    client: TestClient, captured_logs: LogReader
) -> None:
    client.get("/healthz", headers={"X-Request-Id": "req-0100"})

    (record,) = captured_logs()
    assert record["request_id"] == "req-0100"
    assert record["severity"] == "INFO"
    assert record["method"] == "GET"
    assert record["path"] == "/healthz"
    assert record["status"] == 200


def test_an_oversized_request_id_is_not_taken_from_the_caller(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-Id": "x" * 500})

    assert len(response.headers["x-request-id"]) <= 128
