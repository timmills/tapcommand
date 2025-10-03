#!/usr/bin/env bash
set -euo pipefail

PIDS=$(pgrep -f '[n]ode.*vite' || true)
if [[ -z "$PIDS" ]]; then
  echo "No Vite dev server processes found."
else
  for pid in $PIDS; do
    echo "Stopping Vite process $pid"
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
      echo "Force killing Vite process $pid"
      kill -9 "$pid" 2>/dev/null || true
    fi
    echo "Process $pid stopped"
    sleep 0.5
  done
fi

if command -v lsof >/dev/null 2>&1; then
  for port in 5173 5174 5175 5176 5177; do
    if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
      pid=$(lsof -t -i :$port -sTCP:LISTEN 2>/dev/null || true)
      if [[ -n "$pid" ]]; then
        echo "Port $port still in use by $pid; killing"
        kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
      fi
    fi
  done
fi

echo "All Vite dev servers stopped."
