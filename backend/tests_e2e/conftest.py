"""Browser sanity checks: serve the real app (built UI + API) and drive it.

The app runs in-process on a free port with a throwaway SQLite file, serving
frontend/dist — build it first (`npm run build` in frontend/). Each test starts
from a freshly seeded demo board.
"""

import shutil
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import BrowserType, Page

from tiny_kanban.config import REPO_ROOT, Settings
from tiny_kanban.main import create_app
from tiny_kanban.seed import seed_board

DIST = REPO_ROOT / "frontend" / "dist"


def _free_port() -> int:
    """A TCP port nothing listens on right now."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def app_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Base URL of the app, served by uvicorn in a background thread."""
    if not (DIST / "index.html").is_file():
        pytest.exit("frontend/dist is missing: run `npm run build` in frontend/")
    settings = Settings(
        _env_file=None,
        db_path=tmp_path_factory.mktemp("e2e") / "board.db",
        static_dir=DIST,
    )
    port = _free_port()
    config = uvicorn.Config(
        create_app(settings), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            pytest.exit("the app did not start")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict, browser_type: BrowserType
) -> dict:
    """Playwright's own Chromium if installed, else the system one (if any)."""
    if Path(browser_type.executable_path).exists():
        return browser_type_launch_args
    system = shutil.which("chromium") or shutil.which("google-chrome")
    if system is None:  # Playwright's error explains `playwright install`
        return browser_type_launch_args
    return {**browser_type_launch_args, "executable_path": system}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """A window wide enough to show all four demo columns without scrolling."""
    return {**browser_context_args, "viewport": {"width": 1600, "height": 1000}}


@pytest.fixture
def board_page(page: Page, app_url: str) -> Page:
    """The app open on a freshly seeded demo board."""
    reset = page.request.put(
        f"{app_url}/api/board", data=seed_board().model_dump(mode="json")
    )
    assert reset.ok, reset.text()
    page.goto(app_url)
    page.locator(".card").first.wait_for()
    return page
