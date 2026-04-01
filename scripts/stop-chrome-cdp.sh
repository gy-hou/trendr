#!/usr/bin/env bash
# Stop the CDP automation Chrome instance.
# Usage: bash stop-chrome-cdp.sh [PORT]
set -euo pipefail

PORT="${1:-${TRENDR_CDP_PORT:-19222}}"
PIDS=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t || true)
if [ -z "$PIDS" ]; then
  echo "not_running:$PORT"
  exit 0
fi

kill $PIDS || true
sleep 0.6
PIDS2=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t || true)
if [ -n "$PIDS2" ]; then
  kill -9 $PIDS2 || true
fi

echo "stopped:$PORT"
