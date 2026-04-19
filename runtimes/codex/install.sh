#!/usr/bin/env bash
# TrendR — Codex Installer
# Installs TrendR skills into $CODEX_HOME/skills (or ~/.codex/skills).

set -euo pipefail

SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
FORCE=0
MODE="copy"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=1; shift ;;
        --link) MODE="link"; shift ;;
        --copy) MODE="copy"; shift ;;
        -h|--help)
            cat << EOF
Usage: runtimes/codex/install.sh [--force] [--link|--copy]

  --force  Replace existing installed skill directories
  --link   Install skills via symlink
  --copy   Install skills via file copy (default)
EOF
            exit 0
            ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"

echo ""
echo "TrendR — Codex Installer"
echo ""
echo "  Repo:   $SCRIPT_DIR"
echo "  Target: $TARGET_ROOT"
echo "  Mode:   $MODE"
echo ""

if command -v codex >/dev/null 2>&1; then
    echo "  codex CLI found: $(command -v codex)"
else
    echo "  warning: codex CLI not found in PATH; only skills will be installed"
fi
echo ""

cmd=(bash "$SCRIPT_DIR/scripts/install-universal-skills.sh" --runtime codex "--$MODE")
if [[ "$FORCE" = "1" ]]; then
    cmd+=(--force)
fi

"${cmd[@]}"
