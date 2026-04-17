#!/usr/bin/env bash
# setup_cron.sh — configure TrendR daily automation (launchd on macOS, cron on Linux)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_ID="ai.trendr.daily"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_ID}.plist"
LOG_DIR="$HOME/.trendr"

mkdir -p "$LOG_DIR"

# Detect OS
if [[ "$(uname)" == "Darwin" ]]; then
    _setup_launchd() {
        cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_ID}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>cd ${REPO_ROOT} &amp;&amp; export TRENDR_PLATFORM=claude-code &amp;&amp; export TRENDR_CC_MODE=native &amp;&amp; claude --output-format json --max-turns 80 -p "\$(cat scripts/prompts/daily_hotspots.txt)" &gt;&gt; ~/research/logs/daily-\$(date +%Y-%m-%d).log 2&gt;&amp;1</string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>   <integer>8</integer>
    <key>Minute</key> <integer>30</integer>
  </dict>

  <key>NetworkState</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/launchd-daily.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/launchd-daily-err.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>${HOME}</string>
  </dict>
</dict>
</plist>
PLIST

        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"
        echo "✓ launchd job loaded: ${PLIST_ID}"
        echo "  Schedule: daily at 08:30"
        echo "  Logs: ${LOG_DIR}/launchd-daily.log"
        echo ""
        echo "To test immediately: launchctl start ${PLIST_ID}"
        echo "To remove:          launchctl unload ${PLIST_PATH} && rm ${PLIST_PATH}"
    }
    _setup_launchd

else
    # Linux: install crontab entry
    CRON_MARKER="# trendr-daily"
    CRON_LINE="30 8 * * * cd ${REPO_ROOT} && TRENDR_PLATFORM=claude-code TRENDR_CC_MODE=native claude --output-format json --max-turns 80 -p \"\$(cat scripts/prompts/daily_hotspots.txt)\" >> ~/research/logs/daily-\$(date +\\%Y-\\%m-\\%d).log 2>&1 ${CRON_MARKER}"

    # Remove old entry if present, then append new one
    ( crontab -l 2>/dev/null | grep -v "$CRON_MARKER"; echo "$CRON_LINE" ) | crontab -
    echo "✓ cron job installed (daily 08:30)"
    echo "  View with: crontab -l"
    echo "  Remove with: crontab -l | grep -v '${CRON_MARKER}' | crontab -"
fi
