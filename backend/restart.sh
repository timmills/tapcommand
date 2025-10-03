#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/backend-restart.log"
PID_FILE="$SCRIPT_DIR/uvicorn.pid"
VENV_DIR="$SCRIPT_DIR/../venv"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VITE_STOP_SCRIPT="$REPO_ROOT/stop_all_vite.sh"
FRONTEND_DIR="$REPO_ROOT/frontend-v2"
VITE_LOG="$FRONTEND_DIR/vite-dev.out"
VITE_PID="$FRONTEND_DIR/vite.pid"

log() {
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$timestamp] $*" | tee -a "$LOG_FILE"
}

log "Restarting backend service"

if [[ -x "$SCRIPT_DIR/stop.sh" ]]; then
  "$SCRIPT_DIR/stop.sh"
else
  log "stop.sh not found or not executable"
fi

if [[ -x "$VITE_STOP_SCRIPT" ]]; then
  log "Stopping any running Vite dev servers"
  "$VITE_STOP_SCRIPT" || log "stop_all_vite.sh reported an error"
else
  log "stop_all_vite.sh not found or not executable"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  log "Virtual environment not found at $VENV_DIR"
  exit 1
fi

source "$VENV_DIR/bin/activate"

log "Starting uvicorn"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$SCRIPT_DIR/backend.out" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
log "uvicorn started with PID $PID"

if [[ -d "$FRONTEND_DIR" ]]; then
  log "Starting Vite dev server for frontend-v2"
  (
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host > "$VITE_LOG" 2>&1 &
    VITE_PID_VALUE=$!
    echo "$VITE_PID_VALUE" > "$VITE_PID"
    log "Vite dev server started with PID $VITE_PID_VALUE"
  )
else
  log "Frontend directory $FRONTEND_DIR not found"
fi

log "Backend restart completed"
