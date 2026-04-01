#!/usr/bin/env bash
# Start a dedicated Chrome instance for CDP automation.
# Chrome 146+ requires a non-default user-data-dir for --remote-debugging-port.
#
# Usage:  bash start-chrome-cdp.sh [PORT] [PROFILE_INDEX]
#   PORT           CDP debug port (default: 19222)
#   PROFILE_INDEX  Chrome profile to sync cookies from (default: auto-detect first non-Default)
#
# Environment overrides:
#   TRENDR_CDP_PORT       same as PORT arg
#   TRENDR_CDP_DATADIR    custom user-data-dir (default: ~/.openclaw/browser/cdp-automation)
#   TRENDR_CHROME_PROFILE source profile name to sync from (e.g. "Profile 1")
set -euo pipefail

PORT="${1:-${TRENDR_CDP_PORT:-19222}}"
DATA_DIR="${TRENDR_CDP_DATADIR:-${HOME}/.openclaw/browser/cdp-automation}"
CHROME_APP="/Applications/Google Chrome.app"
CHROME_DEFAULT_DIR="${HOME}/Library/Application Support/Google/Chrome"

mkdir -p "$DATA_DIR"

# Reuse if already listening
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "already_listening:$PORT"
  exit 0
fi

if [ ! -d "$CHROME_APP" ]; then
  echo "chrome_not_found" >&2
  exit 1
fi

# Sync cookies from real Chrome profile before launch
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/sync-chrome-profile.sh" ]; then
  TRENDR_CDP_DATADIR="$DATA_DIR" bash "$SCRIPT_DIR/sync-chrome-profile.sh" "${2:-}"
fi

open -na "$CHROME_APP" --args \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$DATA_DIR" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check

# Wait for DevTools HTTP endpoint
for _ in {1..40}; do
  if curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
    echo "ready:$PORT"
    exit 0
  fi
  sleep 0.25
done

echo "not_ready:$PORT" >&2
exit 2
