from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import api
from .config import Settings, get_settings
from .db import make_engine, make_session_factory, session_dependency
from .mcp_server import build_mcp, build_mcp_app
from .service import BoardValidationError, NotFoundError

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _hostname(netloc_or_url: str) -> str | None:
    """Host part of a Host header ("h:port") or Origin ("scheme://h:port")."""
    if "//" not in netloc_or_url:
        netloc_or_url = "//" + netloc_or_url
    try:
        return urlsplit(netloc_or_url).hostname
    except ValueError:
        return None


def foreign_request_reason(request: Request, trusted: frozenset[str]) -> str | None:
    """Why a request must be refused as cross-site, or None if it is local.

    The app is unauthenticated, so this is its only boundary: a Host outside
    `trusted` means DNS rebinding (an attacker's name now pointing at us), an
    Origin outside it means another site's page (CSRF). Browsers send no
    Origin on plain same-origin GETs; "null" (sandboxed/file pages) is refused.
    """
    host = _hostname(request.headers.get("host", ""))
    if host not in trusted:
        return "Request refused: unknown Host header (add it to KANBAN_ALLOWED_HOSTS)"
    origin = request.headers.get("origin")
    if origin is not None and _hostname(origin) not in trusted:
        return "Request refused: cross-site Origin"
    return None


def run_migrations(settings: Settings) -> None:
    """Bring the SQLite schema up to the latest Alembic revision."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.db_url)
    command.upgrade(cfg, "head")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app: REST API, MCP mount, static UI and the local-only guard."""
    settings = settings or get_settings()

    mcp = build_mcp(settings)
    # Builds the session manager the lifespan below runs, so it has to happen
    # before the app starts — mcp.session_manager raises until it is called.
    mcp_app = build_mcp_app(mcp)

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
    async def invalid_board(
        _request: Request, exc: BoardValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    app.dependency_overrides[api.get_session] = session_dependency(session_factory)
    app.dependency_overrides[api.get_settings] = lambda: settings

    app.include_router(api.router)
    app.mount("/mcp", mcp_app)

    # The mounted Starlette app 307-redirects "/mcp" to "/mcp/"; some MCP
    # clients don't follow redirects on POST, so rewrite the path up front
    @app.middleware("http")
    async def _mcp_no_slash(request: Request, call_next):
        if request.scope["path"] == "/mcp":
            request.scope["path"] = "/mcp/"
            request.scope["raw_path"] = b"/mcp/"
        return await call_next(request)

    # Registered last so it runs first: guards /api, /mcp and the static UI
    trusted_hosts = settings.trusted_hosts

    @app.middleware("http")
    async def _local_only(request: Request, call_next):
        """Refuse DNS-rebinding and cross-site requests with a readable 403."""
        reason = foreign_request_reason(request, trusted_hosts)
        if reason is not None:
            return JSONResponse(status_code=403, content={"detail": reason})
        return await call_next(request)

    # Serve the built frontend when available; API-only mode otherwise (dev uses Vite)
    if (settings.static_dir / "index.html").is_file():
        app.mount(
            "/", StaticFiles(directory=settings.static_dir, html=True), name="static"
        )

    return app


app = create_app()
