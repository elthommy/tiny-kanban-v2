# Tiny-kanban v2 — architecture & contributing guide

A dark-themed kanban board with a **React frontend** (display only) and a
**Python backend** (FastAPI + SQLAlchemy 2.0 + Alembic + SQLite) that owns all
logic and data, plus an **MCP server (read + write)** for LLM clients. This file is
the map for anyone — human or LLM agent — making changes.

Design principle: **the frontend stays dumb, logic lives in Python.**
The maintainer is a Python developer; treat `frontend/` as a rendering layer.
Every board rule (archiving, restore targets, ordering, cascades, defaults) is
a function in `backend/src/tiny_kanban/service.py` — add new rules there, never
in React.

## Quick start

```bash
./start.sh          # end user: build UI once, serve app at http://127.0.0.1:8000
./start.sh --build  # same, force UI rebuild (after frontend changes)
./start.sh dev      # development: backend auto-reload + Vite HMR
```

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js/npm.

## Configuration

Copy `.env.example` to `.env` at the repo root (both the backend and Vite read
it there). Everything has defaults; env vars beat `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `KANBAN_BACKEND_PORT` | `8000` | FastAPI port (serves UI + `/api` + `/mcp`) |
| `KANBAN_HOST` | `127.0.0.1` | Backend bind interface |
| `KANBAN_FRONTEND_PORT` | `5173` | Vite dev server port (dev mode only) |
| `KANBAN_DB_PATH` | `backend/data/board.db` | SQLite database file |

Backend settings live in `backend/src/tiny_kanban/config.py` (pydantic-settings,
prefix `KANBAN_`). Add new settings there, never as scattered constants.

## Where is the data stored?

**A SQLite file** at `KANBAN_DB_PATH` (default `backend/data/board.db`,
gitignored).

- Schema is owned by **Alembic migrations** in `backend/alembic/versions/`,
  run automatically at app startup (`run_migrations` in `main.py`).
- Inspect: `sqlite3 backend/data/board.db '.tables'`. Reset: delete the file.
- First `GET /api/board` on a fresh DB seeds the demo board
  (`seed.py`); a `meta` table flag ensures a deliberately emptied board is
  never re-seeded. `meta` also stores the **board version** (see ETag below).
- Tables: `columns`, `cards`, `labels`, `card_labels`, `checklist_items`,
  `meta` — ordering via `position` columns, string ids, FKs cascade on delete.
- Legacy note: pre-backend boards lived in browser `localStorage`; on first
  load the frontend PUTs any such board to the backend, then renames the key.

## How the pieces fit

```
browser ──HTTP──> FastAPI (backend/src/tiny_kanban/)
LLM client ──MCP (streamable HTTP /mcp)──┘
    api.py         REST endpoints — thin wrappers, no rules
    mcp_server.py  MCP tools (read + write) — thin wrappers, no rules
    service.py     ALL board rules + queries        ← the interesting file
    models.py      SQLAlchemy tables    schemas.py  Pydantic (JSON contract)
    seed.py        demo board           config.py   settings + label PALETTE
    db.py          engine/session       main.py     app factory, mounts, migrations
```

### REST API

`GET /api/board` returns the full board (shape = `frontend/src/types.ts`).
Every mutation endpoint **returns the full updated board** plus an
`ETag: "<version>"` header (version = monotonic counter in `meta`, bumped per
mutation). Unknown ids → 404, rule violations → 422 (via exception handlers
in `main.py` for `NotFoundError` / `BoardValidationError`).

| Area | Endpoints |
|---|---|
| Board | `GET /api/board` · `PUT /api/board` (import path; optional `If-Match` → 412 on stale version) |
| Columns | `POST /api/columns` · `PATCH·DELETE /api/columns/{id}` · `POST …/archive-all` · `POST …/cards` |
| Cards | `PATCH·DELETE /api/cards/{id}` · `POST …/move` · `POST …/archive` · `POST …/restore` |
| Card labels | `PUT·DELETE /api/cards/{id}/labels/{labelId}` |
| Checklist | `POST /api/cards/{id}/checklist` · `PATCH·DELETE …/checklist/{itemId}` |
| Labels | `POST /api/labels` · `PATCH·DELETE /api/labels/{id}` |

**JSON contract**: `schemas.py` mirrors `frontend/src/types.ts` (camelCase).
The label color `PALETTE` in `config.py` mirrors `frontend/src/config.ts`.
Change one side → change the other → cover with a round-trip test.

### MCP server (read + write)

Mounted at **`/mcp`** (streamable HTTP) in the same process. Register:

```bash
claude mcp add --transport http tiny-kanban http://127.0.0.1:8000/mcp
```

All tools are thin wrappers over `service.py` — one tool per query/mutation:

- **Read**: `get_board` · `list_cards(query?, column?, label?, archived?)` ·
  `get_card(card_id)`
- **Columns**: `add_column` · `rename_column` · `delete_column` (cards → archive)
  · `archive_all_cards`
- **Cards**: `add_card` (title, description, top/bottom) · `update_card` ·
  `move_card` · `archive_card` · `restore_card` · `delete_card`
- **Card labels / checklist**: `add_card_label` · `remove_card_label` ·
  `add_checklist_item` · `update_checklist_item` · `delete_checklist_item`
- **Labels**: `create_label` (palette color auto-picked) · `rename_label` ·
  `delete_label` (colors are changed in the UI, not via MCP)

`column`/`label` arguments accept an **id or a unique case-insensitive name**
(resolved by `resolve_column_id`/`resolve_label_id` in `service.py` — ambiguous
names are a 422-style tool error); `card_id`/`item_id` are always ids. Write
tools bump the board version like any REST mutation. Concurrency note: the UI
does not poll, so it shows MCP changes after its next structural action or a
reload; UI text edits PATCH only their own fields, so they can't overwrite
unrelated MCP writes.

### Frontend contract

`frontend/src/api.ts` is the only file talking to the backend:

- **Structural actions** (add/move/archive/delete/toggles) call an endpoint,
  and `App.tsx` adopts the returned board wholesale. No board rules in React.
- **Text edits** (card title/description, column title, label name) fire per
  keystroke: local state updates optimistically, `api.ts` debounces a PATCH
  per target (400 ms) and flushes on tab-hide **and before any structural
  call** (so a structural response can't revive stale text).
- Failed structural calls show a dismissible "Sync failed" banner; state keeps
  the last server board.

## Testing

**Backend (the real suite)** — `cd backend && uv run pytest` (~150 tests):

Fixtures in `tests/conftest.py`: `settings` (tmp SQLite), `session` (migrated
DB, for service-level tests), `client` (full-app TestClient incl. lifespan +
MCP mount), payload builders. Files map to layers: `test_service_mutations.py`
(board rules), `test_api_mutations.py` (HTTP), `test_versioning.py`
(ETag/If-Match), `test_mcp.py` / `test_mcp_write.py` (JSON-RPC read/write),
plus the Phase 1 files.
**Every new board rule needs tests at the service and HTTP layers.**

**Frontend (minimal by design)** — `cd frontend && npm test`: only `api.ts`
is covered (debounce, flush ordering, migration). jsdom no longer bundles
`localStorage`; tests stub it (see `api.test.ts`).

## How to add an Alembic migration

1. Edit `models.py` (add a column/table).
2. `cd backend && uv run alembic revision --autogenerate -m "describe change"`
3. Review the generated file — autogenerate is a draft, not a truth. SQLite
   quirks are handled via `render_as_batch` in `alembic/env.py`.
4. `uv run pytest` — migration tests run `upgrade head` on a fresh DB.
5. If the field is part of the board payload: update `schemas.py`,
   `service.py`, `frontend/src/types.ts`, and add a round-trip test.

Migrations run automatically at startup; users never run Alembic by hand.

## How to add a feature (the standard path)

1. Rule → `service.py` function (+ service tests).
2. Endpoint → `api.py` wrapper + request schema in `schemas.py` (+ HTTP tests).
3. UI → add the action in `frontend/src/api.ts`, wire it in `App.tsx`
   (`apply(api.…)`), render in the component.
4. Expose to LLMs? Add an MCP tool wrapper in `mcp_server.py`.

## Gotchas

- `frontend/dist/` and `backend/data/` are build/runtime artifacts, gitignored.
- The `/mcp` mount rewrites the no-trailing-slash path in a middleware in
  `main.py` — without it, Starlette 307-redirects `/mcp` → `/mcp/` and some
  MCP clients fail. DNS-rebinding protection is off (local unauthenticated
  app; the REST API has no Host validation either).
- `window.confirm` guards destructive UI actions (`CONFIRM_DELETE` in
  `frontend/src/config.ts`).
- Don't add a router, state library, or second store to the frontend; extend
  the backend instead.

## Roadmap

Done: SQLite + Alembic (Phase 1) · per-resource API, rules in `service.py`,
board version/ETag, MCP at `/mcp` (Phase 2) · MCP write tools.

Next ideas: due dates · card dependencies (`card_dependencies` table + FK
cascade) — each lands as an Alembic migration.
