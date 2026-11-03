"""Regenerate the README snooze screenshots: dashboard, snooze popup, Snoozed tab.

Serves the built UI + API in-process on a throwaway SQLite file (like the e2e
tests), builds a demo state through the API, and saves 1600px-wide shots at 2x.

    cd frontend && npm run build
    cd backend && uv run --group e2e python ../doc/make_screenshots.py [OUT_DIR]

OUT_DIR defaults to doc/screenshots/. Due and wake-up dates are relative to
today, so the dates in the shots change with the day you run it.
"""

import shutil
import socket
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import uvicorn
from playwright.sync_api import APIRequestContext, Page, sync_playwright

from tiny_kanban.config import REPO_ROOT, Settings
from tiny_kanban.main import create_app
from tiny_kanban.seed import seed_board

WIDTH = 1600


def serve() -> tuple[uvicorn.Server, str]:
    """Start the app on a free port and a throwaway DB; return it and its URL."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    settings = Settings(
        _env_file=None,
        db_path=Path(tempfile.mkdtemp()) / "board.db",
        static_dir=REPO_ROOT / "frontend" / "dist",
    )
    server = uvicorn.Server(
        uvicorn.Config(create_app(settings), port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server, f"http://127.0.0.1:{port}"


def in_days(n: int) -> str:
    """ISO date n days from today."""
    return (date.today() + timedelta(days=n)).isoformat()


def build_demo_state(req: APIRequestContext, url: str) -> None:
    """Demo board with two date snoozes, one card waiting on a prerequisite and
    one that just woke up because its prerequisite was resolved."""
    req.put(f"{url}/api/board", data=seed_board().model_dump(mode="json"))
    req.put(f"{url}/api/cards/c5/snooze", data={"until": in_days(7)})
    req.put(f"{url}/api/cards/c7/snooze", data={"until": in_days(30)})
    req.put(f"{url}/api/cards/c3/dependencies/c6")
    req.put(f"{url}/api/cards/c3/snooze-until-resolved")
    board = req.post(
        f"{url}/api/columns/col1/cards", data={"title": "Recruit participants"}
    ).json()
    prereq = board["columns"][0]["cardIds"][-1]
    req.put(f"{url}/api/cards/c2/dependencies/{prereq}")
    req.put(f"{url}/api/cards/c2/snooze-until-resolved")
    req.delete(f"{url}/api/cards/{prereq}")  # resolves it: c2 wakes up


def shoot_top(page: Page, path: Path, last_selector: str) -> None:
    """Screenshot from the top of the page down to just below an element."""
    box = page.locator(last_selector).first.bounding_box()
    height = box["y"] + box["height"] + 32
    page.screenshot(path=path, clip={"x": 0, "y": 0, "width": WIDTH, "height": height})


def shoot_snooze_popup(page: Page, req: APIRequestContext, url: str, out: Path):
    """Card window with the snooze popup open, incl. the prerequisites option."""
    req.put(f"{url}/api/cards/c1/dependencies/c4")
    page.goto(url)
    page.locator(".card", has_text="Redesign onboarding flow").click()
    page.locator(".modal-footer").get_by_role("button", name="Snooze").click()
    page.set_viewport_size({"width": WIDTH, "height": 1400})
    box = page.locator(".modal").bounding_box()
    page.set_viewport_size(
        {"width": WIDTH, "height": int(box["y"] + box["height"] + 30)}
    )
    page.screenshot(path=out / "tiny-kanban-v2_snooze.png")


def main(out: Path) -> None:
    """Build the demo state, then take the three shots into `out`."""
    server, url = serve()
    with sync_playwright() as p:
        exe = shutil.which("chromium")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(
            viewport={"width": WIDTH, "height": 1000}, device_scale_factor=2
        )
        build_demo_state(page.request, url)
        page.goto(url)
        page.locator(".card").first.wait_for()
        page.evaluate("document.fonts.ready")  # measure with the final font
        shoot_top(page, out / "tiny-kanban-v2_dashboard.png", ".column")
        page.get_by_role("button", name="Snoozed · 3").click()
        shoot_top(page, out / "tiny-kanban-v2_snoozed.png", ".archive-list")
        shoot_snooze_popup(page, page.request, url, out)
        browser.close()
    server.should_exit = True


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "doc" / "screenshots")
