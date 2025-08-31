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

echo "> Start Postgres (docker compose)"
if command -v docker >/dev/null 2>&1; then
  # Try docker compose; if it fails due to permissions, print guidance instead of using sudo
  if ! docker compose -f "$ROOT/docker-compose.db.yml" up -d 2>/dev/null; then
    echo "! docker compose failed to start. You may need to run:"
    echo "  docker compose -f docker-compose.db.yml up -d"
  fi
else
  echo "! docker not found; skipping DB startup" >&2
fi

echo "> Run database migrations"
# Wait a bit more for Postgres to accept connections
sleep 5
alembic upgrade head || echo "! Migration failed, database might already be up to date"

echo "> Export front-end API base URL"
export NEXT_PUBLIC_API_BASE_URL="http://localhost:${API_PORT}"

echo "> Load .env for backend"
set -a
if [ -f "$ROOT/.env" ]; then . "$ROOT/.env"; fi
set +a

cleanup() { echo; echo "Stopping..."; kill ${API_PID:-0} ${WEB_PID:-0} 2>/dev/null || true; }
trap cleanup EXIT

echo "> Launch FastAPI :$API_PORT"
# Limit reload watch to source dirs and exclude the DB volume directory robustly
uvicorn apps.api.main:app \
  --host 0.0.0.0 --port ${API_PORT} \
  --reload \
  --reload-dir apps \
  --reload-dir packages \
  --reload-exclude ".pgdata" \
  --reload-exclude ".pgdata/*" \
  --reload-exclude "**/.pgdata/**" &
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

echo "> Wait for API to be ready..."
for i in {1..60}; do
  if curl -s "http://localhost:${API_PORT}/healthz" >/dev/null; then break; fi
  sleep 1
done

# Open browser (Linux/macOS) unless disabled
if [ "$OPEN_BROWSER" = "1" ]; then
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:${WEB_PORT}" >/dev/null 2>&1 || true; fi
  if command -v open >/dev/null 2>&1; then open "http://localhost:${WEB_PORT}" >/dev/null 2>&1 || true; fi
fi

echo "> Prewarming demo queries (6 total: EN & BN)"
# EN queries
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"google translate new feature","lang":"en"}' >/dev/null || true
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"latest on semiconductor export controls","lang":"en"}' >/dev/null || true
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"Bangladesh inflation this week","lang":"en"}' >/dev/null || true
# BN queries
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"গুগল ট্রান্সলেটের নতুন ফিচার","lang":"bn"}' >/dev/null || true
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"সেমিকন্ডাক্টর রপ্তানি নিয়ন্ত্রণের সর্বশেষ আপডেট","lang":"bn"}' >/dev/null || true
curl -s -X POST "http://localhost:${API_PORT}/ask" -H "content-type: application/json" \
  -d '{"query":"বাংলাদেশে মুদ্রাস্ফীতির সাম্প্রতিক খবর","lang":"bn"}' >/dev/null || true

echo "KhoborAgent running — Ctrl+C to stop"
wait