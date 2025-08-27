#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"

echo "> Stop any stale dev processes"
pkill -f "uvicorn apps.api.main:app" >/dev/null 2>&1 || true
pkill -f "next dev" >/dev/null 2>&1 || true

echo "> Python venv & deps"
if [ ! -d "$ROOT/.venv" ]; then python3 -m venv "$ROOT/.venv"; fi
source "$ROOT/.venv/bin/activate"
pip -q install --upgrade pip >/dev/null
pip -q install -r "$ROOT/requirements.txt"

echo "> Export front-end API base URL"
export NEXT_PUBLIC_API_BASE_URL="http://localhost:${API_PORT}"

cleanup() { echo; echo "Stopping..."; kill ${API_PID:-0} ${WEB_PID:-0} 2>/dev/null || true; }
trap cleanup EXIT

echo "> Launch FastAPI :$API_PORT"
uvicorn apps.api.main:app --host 0.0.0.0 --port ${API_PORT} --reload &
API_PID=$!

echo "> Launch Next.js :$WEB_PORT"
if command -v pnpm >/dev/null 2>&1; then
  # Ensure only one dev server binds the port; use explicit --port and disable automatic open
  (cd "$ROOT/apps/web" && pnpm install && pnpm dev --port ${WEB_PORT} --hostname 0.0.0.0) &
else
  (cd "$ROOT/apps/web" && npm install && npm run dev -- --port ${WEB_PORT} --hostname 0.0.0.0) &
fi
WEB_PID=$!

sleep 2

# Open browser (Linux/macOS) unless disabled
if [ "$OPEN_BROWSER" = "1" ]; then
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:${WEB_PORT}" >/dev/null 2>&1 || true; fi
  if command -v open >/dev/null 2>&1; then open "http://localhost:${WEB_PORT}" >/dev/null 2>&1 || true; fi
fi

echo "> Prewarming demo queries"
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"latest on semiconductor export controls","lang":"bn"}' >/dev/null || true
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"Bangladesh inflation this week","lang":"bn"}' >/dev/null || true

echo "KhoborAgent running — Ctrl+C to stop"
wait