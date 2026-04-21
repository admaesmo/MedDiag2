#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID_FILE="$ROOT_DIR/.run/backend.pid"
FRONTEND_PID_FILE="$ROOT_DIR/.run/frontend.pid"
BACKEND_LOG_FILE="$ROOT_DIR/.run/backend.log"
FRONTEND_LOG_FILE="$ROOT_DIR/.run/frontend.log"

mkdir -p "$ROOT_DIR/.run"

cd "$ROOT_DIR"

load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

load_env_file "$ROOT_DIR/.env"

DATABASE_URL="${DATABASE_URL:-sqlite:///./meddiag.local.db}"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "Python was not found in PATH."
    exit 1
  fi
fi

wait_for_postgres() {
  "$PYTHON_BIN" - <<'PY'
import socket
import time

deadline = time.time() + 60
last_error = None
while time.time() < deadline:
    sock = socket.socket()
    sock.settimeout(1)
    try:
        sock.connect(("127.0.0.1", 5432))
        print("PostgreSQL is reachable.")
        break
    except Exception as exc:
        last_error = exc
        time.sleep(1)
    finally:
        sock.close()
else:
    raise SystemExit(f"PostgreSQL did not become reachable in time: {last_error}")
PY
}

if [[ "$DATABASE_URL" == postgresql* ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required for PostgreSQL mode but was not found in PATH."
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo "docker compose is required for PostgreSQL mode but is not available."
    exit 1
  fi

  echo "Starting PostgreSQL container..."
  docker compose up -d db

  echo "Waiting for PostgreSQL on 127.0.0.1:5432..."
  wait_for_postgres
else
  echo "Using SQLite local database: $DATABASE_URL"
fi

echo "Checking database connectivity..."
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" "$ROOT_DIR/scripts/check-local-db.py"

if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
  echo "Backend already running with PID $(cat "$BACKEND_PID_FILE")."
else
  echo "Starting backend on http://127.0.0.1:8000 ..."
  nohup env PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 \
    >"$BACKEND_LOG_FILE" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
fi

if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
  echo "Frontend already running with PID $(cat "$FRONTEND_PID_FILE")."
else
  echo "Starting frontend on http://127.0.0.1:3000 ..."
  nohup bash -lc "cd '$ROOT_DIR/frontend/web' && npm run dev" \
    >"$FRONTEND_LOG_FILE" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"
fi

echo
echo "Local services started:"
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: http://127.0.0.1:3000"
echo
echo "Logs:"
echo "  Backend:  $BACKEND_LOG_FILE"
echo "  Frontend: $FRONTEND_LOG_FILE"
