"""Host/Origin guard: the unauthenticated app only answers local, same-site requests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tiny_kanban.config import Settings
from tiny_kanban.main import create_app

from .conftest import make_board, make_settings
from .test_static import make_dist

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
MCP_LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


@pytest.fixture
def local_client(tmp_path: Path):
    """Seeded client with production defaults, talking to http://127.0.0.1:8000."""
    settings = make_settings(tmp_path, allowed_hosts=[])
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8000") as c:
        c.get("/api/board")
        yield c


@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost:5173", "[::1]:8000"])
def test_loopback_hosts_allowed(local_client, host):
    assert local_client.get("/api/board", headers={"Host": host}).status_code == 200


def test_rebound_host_refused_on_api(local_client):
    r = local_client.get("/api/board", headers={"Host": "evil.example:8000"})
    assert r.status_code == 403
    assert "Host" in r.json()["detail"]


def test_rebound_host_cannot_replace_board(local_client):
    r = local_client.put(
        "/api/board",
        json=make_board(),
        headers={"Host": "evil.example:8000"},
    )
    assert r.status_code == 403
    assert local_client.get("/api/board").json()["columns"]


def test_rebound_host_refused_on_mcp(local_client):
    headers = {**MCP_HEADERS, "Host": "evil.example:8000"}
    r = local_client.post("/mcp", json=MCP_LIST_TOOLS, headers=headers)
    assert r.status_code == 403


def test_local_mcp_still_works(local_client):
    r = local_client.post("/mcp", json=MCP_LIST_TOOLS, headers=MCP_HEADERS)
    assert r.status_code == 200
    assert r.json()["result"]["tools"]


def test_rebound_host_refused_on_static_ui(tmp_path):
    settings = make_settings(tmp_path, allowed_hosts=[], static_dir=make_dist(tmp_path))
    with TestClient(create_app(settings), base_url="http://localhost") as client:
        assert client.get("/").status_code == 200
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 403


@pytest.mark.parametrize("origin", ["https://evil.example", "null"])
def test_cross_site_post_refused(local_client, origin):
    """The body-less archive-all POST is a CORS simple request — no preflight."""
    r = local_client.post("/api/columns/col1/archive-all", headers={"Origin": origin})
    assert r.status_code == 403
    assert "Origin" in r.json()["detail"]
    board = local_client.get("/api/board").json()
    assert not any(card["archived"] for card in board["cards"].values())


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:8000", "http://localhost:5173", "http://[::1]:8000"]
)
def test_same_site_post_allowed(local_client, origin):
    r = local_client.post("/api/cards/c1/archive", headers={"Origin": origin})
    assert r.status_code == 200


def test_allowed_hosts_setting_admits_lan_name(tmp_path):
    settings = make_settings(tmp_path, allowed_hosts=["Kanban.LAN"])
    with TestClient(create_app(settings), base_url="http://kanban.lan:8000") as c:
        r = c.post(
            "/api/columns", json={"title": "X"}, headers={"Origin": "http://kanban.lan"}
        )
        assert r.status_code == 200


def test_trusted_hosts_include_specific_bind_address():
    s = Settings(_env_file=None, host="192.168.1.10")
    assert "192.168.1.10" in s.trusted_hosts
    assert {"localhost", "127.0.0.1", "::1"} <= s.trusted_hosts


def test_trusted_hosts_skip_wildcard_bind():
    assert "0.0.0.0" not in Settings(_env_file=None, host="0.0.0.0").trusted_hosts


def test_allowed_hosts_env_is_comma_separated(monkeypatch):
    monkeypatch.setenv("KANBAN_ALLOWED_HOSTS", "kanban.lan, 10.0.0.5")
    assert Settings(_env_file=None).allowed_hosts == ["kanban.lan", "10.0.0.5"]


def test_allowed_hosts_default_empty():
    assert Settings(_env_file=None).allowed_hosts == []
