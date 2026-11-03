# Tiny-kanban v2

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/elthommy/tiny-kanban-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/elthommy/tiny-kanban-v2/actions/workflows/ci.yml)

A small dark-themed kanban board ("Flowboard Dark"), implemented from the
[Claude Design](https://claude.ai/design) project *Kanban board design*.

React frontend (display), Python backend (FastAPI + SQLAlchemy + Alembic)
owning all board logic, data in a local SQLite file, and an MCP server so
LLM clients can query **and update** the board:

```bash
claude mcp add --transport http tiny-kanban http://127.0.0.1:8000/mcp
```
## Demo

https://github.com/user-attachments/assets/2d0bec4f-3922-4ad5-82a7-e473bcc66db5

[![Tiny-kanban v2 launch video](./doc/video/tiny-kanban-v2_brag.jpg)](./doc/video/tiny-kanban-v2_brag.mp4)

<sub>Music: "Happy Beats / Business Moves Vol. 1" by Sascha Ende, [ende.app](https://ende.app) — licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).</sub>

## Dashboard
![Board with labels, checklist progress, due-date badges (overdue, due soon, upcoming), snoozed-card counts and a just-woke-up badge](./doc/screenshots/tiny-kanban-v2_dashboard.png)
## Card
![Card details: labels, due date, description, checklist, dependencies, snooze and archive](./doc/screenshots/tiny-kanban-v2_card.png)

<details>
<summary>More screenshots</summary>

### Label editor
![Board-wide label editor: rename, recolor, delete, add](./doc/screenshots/tiny-kanban-v2_labels.png)

### Column menu
![Column menu: add a card, sort by label, archive all cards, delete column](./doc/screenshots/tiny-kanban-v2_column-menu.png)

### Snooze
![Snooze popup: tomorrow, next Monday, in 1 week, in 1 month, until its prerequisites are done or a custom date, with a warning for dates after the due date](./doc/screenshots/tiny-kanban-v2_snooze.png)

### Snoozed cards
![Snoozed cards by wake-up date, then those waiting for prerequisites, with change snooze and wake now](./doc/screenshots/tiny-kanban-v2_snoozed.png)

### Archive
![Archived cards with search, restore to original column, or delete](./doc/screenshots/tiny-kanban-v2_archive.png)

</details>

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and Node.js.

```bash
./start.sh          # build the UI once and serve everything at http://127.0.0.1:8000
./start.sh dev      # development: backend auto-reload + Vite HMR
```

Ports and the database path are configurable — copy `.env.example` to `.env`.

## Features

- Columns: add, rename inline, delete (cards move to the archive), archive all cards
- Cards: add (Enter in the column footer), drag & drop between/within columns
  with a drop indicator, open in a modal
- Card modal: edit title & description, toggle labels, checklist with progress
  bar, snooze, archive or delete
- Snooze: hide a card until a date (tomorrow, next Monday, in 1 week/month, or
  any date) or until its prerequisites are done; it stays in its column and
  reappears on its own with a "Just woke up" badge for the day. Each column
  shows how many cards are snoozed
- Labels: shared across the board — create, rename, recolor (8-color palette),
  delete from the "Edit labels" panel in the card modal
- Snoozed view: cards by wake-up date (then those waiting for prerequisites) —
  wake now or change the snooze
- Archive view: search, restore to the original column, permanently delete

Behavior toggles (confirmation dialogs, new-card position, archive sort order)
live in `frontend/src/config.ts`.

## Tests

```bash
pushd backend
  uv run pytest -v    # the thorough suite
popd
pushd frontend
  npm test        # minimal API-client tests
  npm run build   # needed by the browser tests below
popd
pushd backend
  uv run --group e2e pytest tests_e2e   # browser sanity checks (Chromium)
popd
```

The browser tests use Playwright's Chromium if installed
(`uv run --group e2e playwright install chromium`), else a system `chromium`.

Architecture, data model, and contribution guide (for humans and LLM agents):
see [AGENTS.md](AGENTS.md).

## ⚠️ Disclaimer

**This is a personal learning project** created for educational purposes and to experiment with AI-assisted development. It was built to:
- Explore full-stack development patterns
- Learn new technologies and frameworks
- Test AI development tools and workflows

**Use at your own risk.** While functional, this project is not intended for production use without proper review, testing, and security hardening. See the [LICENSE](LICENSE) for full terms.

## Development

This project was developed with assistance from Claude (Anthropic's AI assistant).

