from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import api
from .config import Settings, get_settings
from .db import make_engine, make_session_factory, session_dependency
from .mcp_server import build_mcp
from .service import BoardValidationError, NotFoundError

BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_migrations(settings: Settings) -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.db_url)
    command.upgrade(cfg, "head")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    mcp = build_mcp(settings)
    # The inner streamable-http app serves at its own configured path; make it
    # "/" so mounting at /mcp doesn't end up as /mcp/mcp
    mcp.settings.streamable_http_path = "/"

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        run_migrations(settings)
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Tiny-kanban", lifespan=lifespan)

    @app.exception_handler(NotFoundError)
    async def not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(BoardValidationError)
    async def invalid_board(_request: Request, exc: BoardValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    app.dependency_overrides[api.get_session] = session_dependency(session_factory)

    app.include_router(api.router)
    app.mount("/mcp", mcp.streamable_http_app())

    # The mounted Starlette app 307-redirects "/mcp" to "/mcp/"; some MCP
    # clients don't follow redirects on POST, so rewrite the path up front
    @app.middleware("http")
    async def _mcp_no_slash(request: Request, call_next):
        if request.scope["path"] == "/mcp":
            request.scope["path"] = "/mcp/"
            request.scope["raw_path"] = b"/mcp/"
        return await call_next(request)

    # Serve the built frontend when available; API-only mode otherwise (dev uses Vite)
    if (settings.static_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")

    return app


app = create_app()
