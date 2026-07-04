from pathlib import Path

from tiny_kanban.config import REPO_ROOT, Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.host == "127.0.0.1"
    assert s.backend_port == 8000
    assert s.db_path == REPO_ROOT / "backend" / "data" / "board.db"
    assert s.static_dir == REPO_ROOT / "frontend" / "dist"


def test_db_url_points_at_db_path(tmp_path: Path):
    s = Settings(_env_file=None, db_path=tmp_path / "x.db")
    assert s.db_url == f"sqlite:///{tmp_path / 'x.db'}"


def test_env_var_overrides(monkeypatch):
    monkeypatch.setenv("KANBAN_BACKEND_PORT", "9999")
    monkeypatch.setenv("KANBAN_HOST", "0.0.0.0")
    monkeypatch.setenv("KANBAN_DB_PATH", "/tmp/custom.db")
    s = Settings(_env_file=None)
    assert s.backend_port == 9999
    assert s.host == "0.0.0.0"
    assert s.db_path == Path("/tmp/custom.db")


def test_env_file_loading(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("KANBAN_BACKEND_PORT=7777\nKANBAN_HOST=192.168.1.10\n")
    s = Settings(_env_file=env_file)
    assert s.backend_port == 7777
    assert s.host == "192.168.1.10"


def test_env_var_beats_env_file(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("KANBAN_BACKEND_PORT=7777\n")
    monkeypatch.setenv("KANBAN_BACKEND_PORT", "8888")
    s = Settings(_env_file=env_file)
    assert s.backend_port == 8888


def test_unknown_env_entries_ignored(tmp_path: Path):
    env_file = tmp_path / ".env"
    # KANBAN_FRONTEND_PORT is consumed by Vite only; the backend must ignore it
    env_file.write_text("KANBAN_FRONTEND_PORT=5199\nKANBAN_BACKEND_PORT=7000\n")
    s = Settings(_env_file=env_file)
    assert s.backend_port == 7000
