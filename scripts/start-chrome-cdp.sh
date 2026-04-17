#!/usr/bin/env bash
# Start a dedicated Chrome instance for CDP automation.
# Chrome 146+ requires a non-default user-data-dir for --remote-debugging-port.
#
# Usage:  bash start-chrome-cdp.sh [PORT] [SOURCE_PROFILE] [CDP_USER]
#   PORT            CDP debug port (default: 19222)
#   SOURCE_PROFILE  Chrome profile to sync cookies from (default: auto-detect first non-Default)
#   CDP_USER        TrendR agent user key for isolated automation store (default: default)
#
# Environment overrides:
#   TRENDR_CDP_PORT        same as PORT arg
#   TRENDR_CDP_DATADIR     custom user-data-dir (overrides CDP_USER routing)
#   TRENDR_CHROME_PROFILE  source profile name to sync from (e.g. "Profile 1")
#   TRENDR_CDP_USER        same as CDP_USER arg
#   TRENDR_CDP_DATA_ROOT   custom root for per-user stores (default: ~/.openclaw/browser/cdp-users)
set -euo pipefail

sanitize_user_key() {
  local raw="${1:-default}"
  local lowered
  lowered="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  local cleaned
  cleaned="$(printf '%s' "$lowered" | tr -cs 'a-z0-9._-' '-')"
  cleaned="${cleaned#-}"
  cleaned="${cleaned%-}"
  printf '%s' "${cleaned:-default}"
}

resolve_data_dir() {
  local user_key="$1"
  local legacy_dir="${HOME}/.openclaw/browser/cdp-automation"
  local root_dir="${TRENDR_CDP_DATA_ROOT:-${HOME}/.openclaw/browser/cdp-users}"
  local scoped_dir="${root_dir}/${user_key}"
  if [ -n "${TRENDR_CDP_DATADIR:-}" ]; then
    printf '%s' "$TRENDR_CDP_DATADIR"
  elif [ "$user_key" = "default" ]; then
    printf '%s' "$legacy_dir"
  else
    printf '%s' "$scoped_dir"
  fi
}

PORT="${1:-${TRENDR_CDP_PORT:-19222}}"
CDP_USER="$(sanitize_user_key "${3:-${TRENDR_CDP_USER:-default}}")"
DATA_DIR="$(resolve_data_dir "$CDP_USER")"
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
  TRENDR_CDP_DATADIR="$DATA_DIR" TRENDR_CDP_USER="$CDP_USER" \
    bash "$SCRIPT_DIR/sync-chrome-profile.sh" "${2:-}" "$CDP_USER"
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
