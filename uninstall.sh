#!/usr/bin/env bash
# TrendR — Uninstall Dispatcher v1.1.1
# Routes to runtimes/openclaw/uninstall.sh or runtimes/claude-code/uninstall.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── colors ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
DIM='\033[2m'

# ── parse flags ─────────────────────────────────────────────────
mode=""
scope="project"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --openclaw)    mode="openclaw";    shift ;;
        --codex)       mode="codex";       shift ;;
        --claude-code) mode="claude-code"; shift ;;
        --all)         mode="all";         shift ;;
        --user)        scope="user";       shift ;;
        --project)     scope="project";    shift ;;
        --dry-run)     DRY_RUN=1;          shift ;;
        -h|--help)
            cat << EOF
Usage: ./uninstall.sh [--openclaw|--codex|--claude-code|--all] [--user|--project] [--dry-run]

  --openclaw    Uninstall OpenClaw runtime files
  --codex       Uninstall Codex runtime files
  --claude-code Uninstall Claude Code runtime files
  --all         Uninstall all runtimes
  --user        (claude-code) target ~/.claude/ scope
  --project     (claude-code) target repo .claude/ scope (default)
  --dry-run     List actions without executing (claude-code only)

No flag: interactive menu
EOF
            exit 0 ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

# ── banner ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}TrendR — Uninstaller${NC}"
echo ""

# ── interactive menu (no flag) ───────────────────────────────────
if [[ -z "$mode" ]]; then
    echo -e "  ${BOLD}Select runtime to uninstall:${NC}"
    echo ""
    echo -e "  ${GREEN}[1] OpenClaw${NC}    — remove agents & skills from ~/.openclaw/workspace/"
    echo -e "  ${BLUE}[2] Codex${NC}       — remove installed skills from \$CODEX_HOME/skills or ~/.codex/skills"
    echo -e "  ${CYAN}[3] Claude Code${NC} — remove agent stubs & commands from .claude/"
    echo -e "  ${YELLOW}[4] All${NC}       — uninstall all runtimes"
    echo -e "  ${RED}[q] Exit${NC}"
    echo ""
    printf "  Enter choice [1/2/3/4/q] (default: 1): "
    read -r MENU_INPUT

    case "${MENU_INPUT:-1}" in
        1)   mode="openclaw"    ;;
        2)   mode="codex"       ;;
        3)   mode="claude-code" ;;
        4)   mode="all"         ;;
        q|Q) echo ""; echo -e "${YELLOW}Cancelled.${NC}"; echo ""; exit 0 ;;
        *)   echo -e "${RED}Invalid choice.${NC}"; exit 1 ;;
    esac
fi

# ── export env for sub-scripts ───────────────────────────────────
export DRY_RUN SCRIPT_DIR scope

# ── dispatch ─────────────────────────────────────────────────────
case "$mode" in
    openclaw)
        bash "$SCRIPT_DIR/runtimes/openclaw/uninstall.sh"
        ;;
    codex)
        bash "$SCRIPT_DIR/runtimes/codex/uninstall.sh"
        ;;
    claude-code)
        bash "$SCRIPT_DIR/runtimes/claude-code/uninstall.sh"
        ;;
    all)
        echo -e "${BOLD}── OpenClaw ─────────────────────────────────────────────────${NC}"
        bash "$SCRIPT_DIR/runtimes/openclaw/uninstall.sh"
        echo ""
        echo -e "${BOLD}── Codex ───────────────────────────────────────────────────${NC}"
        bash "$SCRIPT_DIR/runtimes/codex/uninstall.sh"
        echo ""
        echo -e "${BOLD}── Claude Code ──────────────────────────────────────────────${NC}"
        bash "$SCRIPT_DIR/runtimes/claude-code/uninstall.sh"
        ;;
    *)
        echo "Internal error: unknown mode '$mode'" >&2
        exit 2
        ;;
esac
