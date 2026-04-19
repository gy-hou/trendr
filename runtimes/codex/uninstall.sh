#!/usr/bin/env bash
# TrendR — Codex Uninstaller
# Removes TrendR skills from $CODEX_HOME/skills (or ~/.codex/skills).

set -euo pipefail

TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"

CORE_SKILLS=(
  "paper-scout"
  "paper-analyzer"
  "review-writer"
  "verifier"
  "research-vault"
  "trendr-watchdog"
  "platform-hotspots"
  "chrome-cdp-setup"
)

echo ""
echo "TrendR — Codex Uninstall"
echo ""
echo "  Target: $TARGET_ROOT"
echo ""

for skill in "${CORE_SKILLS[@]}"; do
    path="$TARGET_ROOT/$skill"
    if [[ -e "$path" || -L "$path" ]]; then
        rm -rf "$path"
        echo "  removed skills/$skill"
    fi
done

echo ""
echo "  The repo content is NOT removed."
echo "  Existing research outputs under ~/research/ are NOT touched."
echo ""
