#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/backend-stop.log"
PID_FILE="$SCRIPT_DIR/uvicorn.pid"

log() {
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$timestamp] $*" | tee -a "$LOG_FILE"
}

log "Stopping backend service"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    log "Sending SIGTERM to process $PID"
    kill "$PID" && log "Process $PID terminated"
  else
    log "No running process with PID $PID found"
  fi
  rm -f "$PID_FILE"
else
  log "PID file not found; attempting to kill uvicorn processes"
  pkill -f "uvicorn" && log "Terminated lingering uvicorn processes" || log "No uvicorn process found"
fi

log "Backend stop completed"
