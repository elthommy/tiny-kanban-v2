from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (backend/src/tiny_kanban/config.py -> three parents up from this file's dir)
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """All runtime configuration, overridable via KANBAN_* env vars or the repo-root .env."""

    model_config = SettingsConfigDict(
        env_prefix="KANBAN_",
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    backend_port: int = 8000
    db_path: Path = REPO_ROOT / "backend" / "data" / "board.db"
    static_dir: Path = REPO_ROOT / "frontend" / "dist"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"


def get_settings() -> Settings:
    return Settings()
