# Tiny-kanban v2 — architecture & contributing guide

A dark-themed kanban board with a **React frontend** (display only) and a
**Python backend** (FastAPI + SQLAlchemy 2.0 + Alembic + SQLite) that owns the
data. This file is the map for anyone — human or LLM agent — making changes.

Design principle: **the frontend stays dumb, logic accumulates in Python.**
The maintainer is a Python developer; treat `frontend/` as a rendering layer
and put anything interesting (rules, validation, future features) in
`backend/`. Currently in **Phase 1** (see roadmap at the bottom).

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
| `KANBAN_BACKEND_PORT` | `8000` | FastAPI port (serves UI + `/api`) |
| `KANBAN_HOST` | `127.0.0.1` | Backend bind interface |
| `KANBAN_FRONTEND_PORT` | `5173` | Vite dev server port (dev mode only) |
| `KANBAN_DB_PATH` | `backend/data/board.db` | SQLite database file |

Backend settings live in `backend/src/tiny_kanban/config.py` (pydantic-settings,
prefix `KANBAN_`). Add new settings there, never as scattered constants.

## Where is the data stored?

**A SQLite file** at `KANBAN_DB_PATH` (default `backend/data/board.db`,
gitignored). No other store — `localStorage` is legacy (see Migration note).

- Schema is owned by **Alembic migrations** in `backend/alembic/versions/`.
  They run automatically at app startup (`run_migrations` in `main.py`).
- Inspect: `sqlite3 backend/data/board.db '.tables'` or any SQLite tool.
- Reset: delete the file; next launch recreates it and seeds the demo board.
- First launch seeds the demo board from `backend/src/tiny_kanban/seed.py`.
  A `meta` table flag distinguishes "fresh DB" from "user emptied the board",
  so a deliberately empty board is never re-seeded.
- **Migration note:** the pre-backend version stored the board in browser
  `localStorage`. On first load the frontend pushes any such board to the
  backend, then renames the key to `flowboard-kanban-dark-v1-migrated`.

Tables: `columns`, `cards`, `labels`, `card_labels` (label order per card),
`checklist_items`, `meta` — all ordering via `position` columns, ids are
client-generated strings, FKs cascade on delete.

## How the pieces fit

```
browser ──HTTP──> FastAPI (backend/src/tiny_kanban/)
                    api.py      GET/PUT /api/board, /api/health
                    service.py  board assembly, validation, replace  ← logic lives here
                    models.py   SQLAlchemy tables
                    schemas.py  Pydantic models = JSON contract (mirrors frontend types.ts)
                    seed.py     demo board
                    config.py   settings        db.py  engine/session
                    main.py     app factory, migrations at startup, serves frontend/dist
```

**Phase 1 API is coarse**: the frontend GETs the whole board on load and PUTs
the whole board (debounced 400 ms) after every change. `service.replace_board`
validates referential integrity (unknown ids, duplicates, archived-but-placed
cards → HTTP 422) and does a transactional full replace.

**JSON contract**: `schemas.py` and `frontend/src/types.ts` must stay in sync
(camelCase fields, e.g. `cardIds`, `archivedFrom`). Change one → change the
other → cover it with a round-trip test.

Frontend (`frontend/src/`): `App.tsx` holds board state in a single `useState`
and defines all action handlers; components under `components/` are
presentational; `storage.ts` is the only file talking to the API; behavior
toggles in `config.ts`; all styling in `index.css`.

## Testing

**Backend (the real suite)** — pytest, in `backend/tests/`:

```bash
cd backend && uv run pytest
```

Fixtures in `conftest.py` give you: `settings` (tmp SQLite), `session`
(migrated DB + SQLAlchemy session, for service-level tests), `client`
(full-app `TestClient`, migrations included), plus payload builders
(`make_board`, `make_card`, `simple_board`…). To add a test: pick the file
matching the layer (`test_service.py` for logic, `test_api_board.py` for
HTTP behavior, `test_migrations.py`, `test_config.py`, `test_static.py`),
take `client` or `session` as an argument, done — each test gets a fresh
database. Every new endpoint or board rule needs tests at both the service
and HTTP layers.

**Frontend (minimal by design)** — Vitest, colocated `*.test.ts`:

```bash
cd frontend && npm test
```

Only `storage.ts` (the API client) is covered. Note: jsdom no longer bundles
`localStorage`; tests stub it (see `storage.test.ts`).

## How to add an Alembic migration

1. Edit `backend/src/tiny_kanban/models.py` (add a column/table).
2. `cd backend && uv run alembic revision --autogenerate -m "describe change"`
3. Review the generated file in `alembic/versions/` — autogenerate is a draft,
   not a truth. SQLite quirks are handled via `render_as_batch` in
   `alembic/env.py`.
4. `uv run pytest` — migration tests run `upgrade head` on a fresh DB.
5. If the field is part of the board payload: update `schemas.py`,
   `service.py`, `frontend/src/types.ts`, and add a round-trip test.

Migrations run automatically at startup; users never run Alembic by hand.

## Gotchas

- `frontend/dist/` and `backend/data/` are build/runtime artifacts, gitignored.
- **Last writer wins**: the whole-board PUT means concurrent writers (e.g. a
  future MCP client) can be silently overwritten. Until Phase 2 adds
  fine-grained endpoints + ETag, nothing but the single browser tab should write.
- `window.confirm` guards destructive UI actions (`CONFIRM_DELETE` in
  `frontend/src/config.ts`).
- Don't add a router, state library, or second store to the frontend; extend
  the backend instead.

## Roadmap (Phase 2+)

1. Per-resource endpoints (`POST /api/cards`, `PATCH /api/cards/{id}`, …) and
   move mutation logic from `App.tsx` into `service.py`.
2. ETag/version guard on writes (kills the last-writer-wins hazard).
3. MCP server (Python SDK) sharing `service.py` — **read-only first**, writes
   only after per-resource endpoints exist.
4. Future data model ideas: due dates, card dependencies (`card_dependencies`
   table + FK cascade) — each lands as an Alembic migration.
