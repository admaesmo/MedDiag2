#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID_FILE="$ROOT_DIR/.run/backend.pid"
FRONTEND_PID_FILE="$ROOT_DIR/.run/frontend.pid"

stop_pid_file() {
  local label="$1"
  local pid_file="$2"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping $label (PID $pid)..."
      kill "$pid"
    else
      echo "$label PID file exists but process is not running."
    fi
    rm -f "$pid_file"
  else
    echo "$label is not tracked as running."
  fi
}

stop_pid_file "backend" "$BACKEND_PID_FILE"
stop_pid_file "frontend" "$FRONTEND_PID_FILE"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Stopping PostgreSQL container..."
  (cd "$ROOT_DIR" && docker compose stop db >/dev/null 2>&1 || true)
fi

echo "Done."
