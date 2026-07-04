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


# Default label colors, cycled through when a label is created without explicit
# colors. Mirrors PALETTE in frontend/src/config.ts (used there for the picker UI)
# — keep the two in sync.
PALETTE: list[dict[str, str]] = [
    {"bg": "#33265A", "fg": "#C9B0F0", "dot": "#8B5CF6"},
    {"bg": "#4A2620", "fg": "#E06A54", "dot": "#E0553C"},
    {"bg": "#1F3A57", "fg": "#9CC6F0", "dot": "#3E88C7"},
    {"bg": "#4A3B18", "fg": "#E8CF8F", "dot": "#D9A521"},
    {"bg": "#1D4238", "fg": "#93D9BE", "dot": "#2E9E78"},
    {"bg": "#4A2038", "fg": "#F0A6C9", "dot": "#D63B82"},
    {"bg": "#16403F", "fg": "#8FD6D9", "dot": "#22A6AD"},
    {"bg": "#2E313A", "fg": "#B7BDCB", "dot": "#8892A6"},
]


def get_settings() -> Settings:
    return Settings()
