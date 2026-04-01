#!/usr/bin/env bash
# Sync cookies/sessions from a real Chrome profile to the CDP automation directory.
# Chrome 146+ requires a non-default user-data-dir for --remote-debugging-port,
# so we maintain a separate dir and sync auth data before each launch.
# macOS keychain cookie encryption key is per-app (not per-dir), so copies decrypt fine.
#
# Usage: bash sync-chrome-profile.sh [PROFILE_NAME]
#   PROFILE_NAME  e.g. "Profile 1", "Default" (default: auto-detect first non-Default)
#
# Environment overrides:
#   TRENDR_CDP_DATADIR       target data dir (default: ~/.openclaw/browser/cdp-automation)
#   TRENDR_CHROME_PROFILE    same as PROFILE_NAME arg
set -euo pipefail

CHROME_DIR="${HOME}/Library/Application Support/Google/Chrome"
DST_BASE="${TRENDR_CDP_DATADIR:-${HOME}/.openclaw/browser/cdp-automation}"
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
