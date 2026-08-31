"""Serving the built web app from the same origin as the API — seam S1."""

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.conftest import BUNDLE_JS, INDEX_HTML
from core.config import Settings


def test_the_root_url_serves_the_built_web_app(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.text == INDEX_HTML
    assert response.headers["content-type"].startswith("text/html")


def test_built_assets_are_served_as_themselves(client: TestClient) -> None:
    response = client.get("/assets/index.js")

    assert response.status_code == 200
    assert response.text == BUNDLE_JS


def test_an_unknown_path_falls_back_to_the_single_page_app(client: TestClient) -> None:
    response = client.get("/console/handovers")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_missing_asset_is_not_answered_with_the_page(client: TestClient) -> None:
    """A 404 on a real asset must stay a 404, or a broken bundle looks like a working page."""
    response = client.get("/assets/does-not-exist.js")

    assert response.status_code == 404


def test_nothing_is_served_when_the_web_app_has_not_been_built(tmp_path: Path) -> None:
    with TestClient(create_app(settings=Settings(), web_dist=tmp_path / "never-built")) as client:
        assert client.get("/").status_code == 404


def test_an_unknown_api_path_is_not_answered_with_the_page(client: TestClient) -> None:
    """An unregistered API route must 404, or a typo looks healthy to a client and a probe."""
    response = client.get("/api/not-a-route")

    assert response.status_code == 404
