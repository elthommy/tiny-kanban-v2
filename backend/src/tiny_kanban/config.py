from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Repo root (backend/src/tiny_kanban/config.py -> three parents up from this file's dir)
REPO_ROOT = Path(__file__).resolve().parents[3]

# Host names every request may carry in its Host/Origin header (any port)
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# Bind addresses meaning "all interfaces" — not a name a browser ever sends
WILDCARD_BINDS = frozenset({"0.0.0.0", "::"})


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
    # Hard dependency rule: refuse moving a card with unresolved prerequisites
    # into the last column (off = soft rule, blocked cards move freely)
    strict_dependencies: bool = False
    # Extra host names (comma-separated) accepted in Host/Origin headers on top
    # of loopback and KANBAN_HOST — e.g. "kanban.lan,192.168.1.10" for a LAN bind
    allowed_hosts: Annotated[list[str], NoDecode] = []

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        """Accept KANBAN_ALLOWED_HOSTS as a comma-separated string."""
        if isinstance(value, str):
            return [h.strip() for h in value.split(",") if h.strip()]
        return value

    @property
    def db_url(self) -> str:
        """SQLAlchemy URL of the SQLite database file."""
        return f"sqlite:///{self.db_path}"

    @property
    def trusted_hosts(self) -> frozenset[str]:
        """Lower-cased host names the app answers to (DNS-rebinding/CSRF guard)."""
        hosts = set(LOOPBACK_HOSTS) | {h.lower() for h in self.allowed_hosts}
        if self.host not in WILDCARD_BINDS:
            hosts.add(self.host.strip("[]").lower())
        return frozenset(hosts)


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
    {"bg": "#4A2F18", "fg": "#F0B98A", "dot": "#E8802E"},
    {"bg": "#33401A", "fg": "#C5E08F", "dot": "#8DB82E"},
    {"bg": "#262D5A", "fg": "#AEB8F0", "dot": "#5B6BE0"},
    {"bg": "#3D2E24", "fg": "#D4B89C", "dot": "#9C7353"},
]


def get_settings() -> Settings:
    return Settings()
