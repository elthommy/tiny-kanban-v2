from pathlib import Path

from fastapi.testclient import TestClient

from tiny_kanban.main import create_app

from .conftest import make_settings


def make_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>tiny-kanban</body></html>")
    (dist / "app.js").write_text("console.log('hi')")
    return dist


def test_serves_index_html_when_dist_exists(tmp_path):
    settings = make_settings(tmp_path, static_dir=make_dist(tmp_path))
    with TestClient(create_app(settings)) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "tiny-kanban" in r.text


def test_serves_assets_when_dist_exists(tmp_path):
    settings = make_settings(tmp_path, static_dir=make_dist(tmp_path))
    with TestClient(create_app(settings)) as client:
        assert client.get("/app.js").status_code == 200


def test_api_not_shadowed_by_static_mount(tmp_path):
    settings = make_settings(tmp_path, static_dir=make_dist(tmp_path))
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_missing_dist_keeps_api_working(tmp_path):
    settings = make_settings(tmp_path)  # static_dir points at a non-existent dir
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 404
