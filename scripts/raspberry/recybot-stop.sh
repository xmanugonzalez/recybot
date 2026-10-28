#!/usr/bin/env bash
set -Eeuo pipefail

RUNTIME_DIR="$HOME/.local/state/recybot"
PID_FILE="$RUNTIME_DIR/dev.pid"

pkill -TERM -f 'chromium.*127\.0\.0\.1:5173' 2>/dev/null || true

if [[ -f "$PID_FILE" ]]; then
  pid="$(<"$PID_FILE")"
  kill -TERM "$pid" 2>/dev/null || true
  for _ in {1..20}; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
fi

for port in 5173 8080 8765 8766; do
  fuser -k -TERM "$port/tcp" 2>/dev/null || true
done

rm -f "$PID_FILE"
