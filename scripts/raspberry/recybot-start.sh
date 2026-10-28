#!/usr/bin/env bash
set -Eeuo pipefail

ROOT='/home/smatipitouchpi3/recybot'
RUNTIME_DIR="$HOME/.local/state/recybot"
LOG_FILE="$RUNTIME_DIR/dev.log"
PID_FILE="$RUNTIME_DIR/dev.pid"
export PATH='/home/smatipitouchpi3/.local/node/bin:/home/smatipitouchpi3/.local/bin':"$PATH"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"

mkdir -p "$RUNTIME_DIR"

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(<"$PID_FILE")" 2>/dev/null
}

wait_for() {
  local url="$1"
  local attempts=60
  until curl -fsS --max-time 1 "$url" >/dev/null 2>&1; do
    ((attempts--))
    (( attempts > 0 )) || return 1
    sleep 1
  done
}

if ! is_running; then
  rm -f "$PID_FILE"
  for port in 5173 8080 8765 8766; do
    fuser -k -TERM "$port/tcp" 2>/dev/null || true
  done
  pkill -TERM -f 'camera/(stream_server|camera_server)\.py' 2>/dev/null || true
  sleep 2
  cd "$ROOT"
  nohup pnpm dev >>"$LOG_FILE" 2>&1 &
  echo "$!" > "$PID_FILE"
fi

wait_for 'http://127.0.0.1:8765/api/camara/status'
wait_for 'http://127.0.0.1:8080/api/camara/status'
wait_for 'http://127.0.0.1:8766/api/salud'
wait_for 'http://127.0.0.1:5173/'

if ! pgrep -f 'chromium.*127\.0\.0\.1:5173' >/dev/null 2>&1; then
  nohup chromium --ozone-platform=wayland --disable-gpu --password-store=basic \
    --kiosk --no-first-run --no-default-browser-check \
    --user-data-dir="$HOME/.config/chromium-recybot" \
    http://127.0.0.1:5173/ >/dev/null 2>&1 &
fi
