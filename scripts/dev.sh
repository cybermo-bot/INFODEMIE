#!/usr/bin/env bash
# Start the Docker services, then the API, the Celery worker and the web app.
# Ctrl-C stops the three processes; the Docker services keep running (`make services-down`).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed: see docs/setup-windows.md, step 3." >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo ".env is missing: copy .env.example to .env and fill it in." >&2
  exit 1
fi

docker compose -f infra/docker-compose.yml up -d --wait
uv --directory apps/api run alembic upgrade head

pids=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

make --no-print-directory api & pids+=($!)
make --no-print-directory worker & pids+=($!)
make --no-print-directory web & pids+=($!)

echo "API http://localhost:8000/docs · Web http://localhost:3000 · Mailpit http://localhost:8025"
wait -n
