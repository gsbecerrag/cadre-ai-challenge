"""The health endpoint — seam S1."""

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from core.config import Settings


def test_healthz_names_the_service_and_version(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"service": "cadre-support-agent", "version": "0.1.0"}


def test_healthz_is_also_reachable_under_the_api_prefix(client: TestClient) -> None:
    """Google's frontend answers `/healthz` on *.run.app itself, so the request never reaches
    the container. `/api/healthz` is the path that is actually probeable in production."""
    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == client.get("/healthz").json()


def test_the_version_comes_from_configuration(web_dist: Path) -> None:
    settings = Settings(app_version="a1b2c3d")

    with TestClient(create_app(settings=settings, web_dist=web_dist)) as client:
        assert client.get("/healthz").json()["version"] == "a1b2c3d"


def test_healthz_answers_before_the_web_app_is_built(tmp_path: Path) -> None:
    """Cloud Run's probe must not depend on `web/dist` existing (it does not in `make dev`)."""
    with TestClient(create_app(settings=Settings(), web_dist=tmp_path / "never-built")) as client:
        assert client.get("/healthz").status_code == 200
