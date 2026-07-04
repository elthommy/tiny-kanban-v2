from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import api
from .config import Settings, get_settings
from .db import make_engine, make_session_factory, session_dependency

BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_migrations(settings: Settings) -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.db_url)
    command.upgrade(cfg, "head")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        run_migrations(settings)
        yield

    app = FastAPI(title="Tiny-kanban", lifespan=lifespan)

    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    app.dependency_overrides[api.get_session] = session_dependency(session_factory)

    app.include_router(api.router)

    # Serve the built frontend when available; API-only mode otherwise (dev uses Vite)
    if (settings.static_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")

    return app


app = create_app()
