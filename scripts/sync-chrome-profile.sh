#!/usr/bin/env bash
# Sync cookies/sessions from a real Chrome profile to the CDP automation directory.
# Chrome 146+ requires a non-default user-data-dir for --remote-debugging-port,
# so we maintain a separate dir and sync auth data before each launch.
# macOS keychain cookie encryption key is per-app (not per-dir), so copies decrypt fine.
#
# Usage: bash sync-chrome-profile.sh [PROFILE_NAME] [CDP_USER]
#   PROFILE_NAME  e.g. "Profile 1", "Default" (default: auto-detect first non-Default)
#   CDP_USER      TrendR agent user key for isolated automation store (default: default)
#
# Environment overrides:
#   TRENDR_CDP_DATADIR       target data dir (overrides CDP_USER routing)
#   TRENDR_CHROME_PROFILE    same as PROFILE_NAME arg
#   TRENDR_CDP_USER          same as CDP_USER arg
#   TRENDR_CDP_DATA_ROOT     custom root for per-user stores (default: ~/.openclaw/browser/cdp-users)
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

resolve_dst_base() {
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

CHROME_DIR="${HOME}/Library/Application Support/Google/Chrome"
CDP_USER="$(sanitize_user_key "${2:-${TRENDR_CDP_USER:-default}}")"
DST_BASE="$(resolve_dst_base "$CDP_USER")"
DST="$DST_BASE/Default"

# Determine source profile
PROFILE="${1:-${TRENDR_CHROME_PROFILE:-}}"
if [ -z "$PROFILE" ]; then
  # Auto-detect: pick the first "Profile N" directory that exists
  for p in "$CHROME_DIR"/Profile\ *; do
    if [ -d "$p" ]; then
      PROFILE="$(basename "$p")"
      break
    fi
  done
fi
# Fallback to Default
PROFILE="${PROFILE:-Default}"
SRC="$CHROME_DIR/$PROFILE"

if [ ! -d "$SRC" ]; then
  echo "sync:skip:no_source ($SRC)" >&2
  exit 0
fi

mkdir -p "$DST"

# Copy essential auth/session files
for f in "Cookies" "Cookies-journal" "Login Data" "Login Data-journal" "Web Data" "Web Data-journal"; do
  [ -f "$SRC/$f" ] && cp -f "$SRC/$f" "$DST/$f"
done

# Copy storage directories
for d in "Local Storage" "Session Storage" "IndexedDB" "Sessions"; do
  if [ -d "$SRC/$d" ]; then
    rm -rf "$DST/$d"
    cp -a "$SRC/$d" "$DST/$d"
  fi
done

# Do NOT copy Local State — it contains all profile entries and would
# re-create extra profiles in the automation directory.

echo "sync:done (from $PROFILE)"
