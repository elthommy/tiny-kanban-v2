#!/usr/bin/env bash
# Tiny-kanban launcher.
#
#   ./start.sh           production mode: build the UI once, serve everything
#                        from a single backend process at http://127.0.0.1:8000
#   ./start.sh --build   same, but force a rebuild of the UI first
#   ./start.sh dev       development mode: backend with auto-reload + Vite dev
#                        server with HMR (two processes, Ctrl-C stops both)
#
# Ports and paths are configured via a repo-root .env file (see .env.example).
set -euo pipefail
cd "$(dirname "$0")"

command -v uv >/dev/null || { echo "error: uv is required — install it from https://docs.astral.sh/uv/" >&2; exit 1; }
command -v npm >/dev/null || { echo "error: npm is required — install Node.js from https://nodejs.org/" >&2; exit 1; }

# shellcheck disable=SC1091
[ -f .env ] && set -a && . ./.env && set +a
BACKEND_PORT="${KANBAN_BACKEND_PORT:-8000}"
HOST="${KANBAN_HOST:-127.0.0.1}"
FRONTEND_PORT="${KANBAN_FRONTEND_PORT:-5173}"

MODE="${1:-serve}"

echo "==> Installing backend dependencies (uv sync)"
(cd backend && uv sync --quiet)

if [ "$MODE" = "dev" ]; then
    echo "==> Installing frontend dependencies"
    (cd frontend && npm install --silent)
    echo "==> Starting backend (http://$HOST:$BACKEND_PORT) and frontend (http://localhost:$FRONTEND_PORT)"
    trap 'kill 0' INT TERM EXIT
    (cd backend && uv run uvicorn tiny_kanban.main:app --host "$HOST" --port "$BACKEND_PORT" --reload) &
    (cd frontend && npm run dev) &
    wait
else
    if [ "$MODE" = "--build" ] || [ ! -f frontend/dist/index.html ]; then
        echo "==> Building frontend"
        (cd frontend && npm install --silent && npm run build)
    fi
    echo "==> Tiny-kanban running at http://$HOST:$BACKEND_PORT"
    (cd backend && exec uv run uvicorn tiny_kanban.main:app --host "$HOST" --port "$BACKEND_PORT")
fi
