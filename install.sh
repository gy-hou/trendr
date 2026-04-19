#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║  TrendR v2.1.0 — Installer Dispatcher                           ║
# ║  Claude Code primary · OpenClaw legacy support                  ║
# ╚══════════════════════════════════════════════════════════════════╝

set -e
VERSION="2.1.0"
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
Usage: ./install.sh [--openclaw|--codex|--claude-code|--all] [--user|--project] [--dry-run]

  --openclaw    Install for OpenClaw runtime (default interactive choice)
  --codex       Install for Codex runtime
  --claude-code Install for Claude Code runtime
  --all         Install for all runtimes
  --user        (claude-code) install into ~/.claude/ instead of repo .claude/
  --project     (claude-code) install into repo .claude/ (default)
  --dry-run     List actions without executing (claude-code only)

No flag: interactive menu
EOF
            exit 0 ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

# ── banner ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║              TrendR v${VERSION} — Installer                       ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── interactive menu (no flag) ───────────────────────────────────
if [[ -z "$mode" ]]; then
    echo -e "  ${BOLD}Select runtime to install for:${NC}"
    echo ""
    echo -e "  ${CYAN}[1] Claude Code${NC} — install agent stubs & commands into .claude/ (default)"
    echo -e "  ${BLUE}[2] Codex${NC}       — install skills into \$CODEX_HOME/skills or ~/.codex/skills"
    echo -e "  ${GREEN}[3] OpenClaw${NC}   — install agents & skills into ~/.openclaw/workspace/ (legacy, still supported)"
    echo -e "  ${YELLOW}[4] All${NC}       — install for all runtimes"
    echo -e "  ${RED}[q] Exit${NC}"
    echo ""
    printf "  Enter choice [1/2/3/4/q] (default: 1): "
    read -r MENU_INPUT

    case "${MENU_INPUT:-1}" in
        1)   mode="claude-code" ;;
        2)   mode="codex"       ;;
        3)   mode="openclaw"    ;;
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
        echo -e "  ${GREEN}▶ Installing for OpenClaw...${NC}"
        echo ""
        bash "$SCRIPT_DIR/runtimes/openclaw/install.sh"
        ;;
    codex)
        echo -e "  ${BLUE}▶ Installing for Codex...${NC}"
        echo ""
        bash "$SCRIPT_DIR/runtimes/codex/install.sh"
        ;;
    claude-code)
        echo -e "  ${CYAN}▶ Installing for Claude Code...${NC}"
        echo ""
        bash "$SCRIPT_DIR/runtimes/claude-code/install.sh"
        ;;
    all)
        echo -e "  ${BLUE}▶ Installing for all runtimes...${NC}"
        echo ""
        echo -e "${BOLD}── OpenClaw ─────────────────────────────────────────────────${NC}"
        bash "$SCRIPT_DIR/runtimes/openclaw/install.sh"
        echo ""
        echo -e "${BOLD}── Codex ───────────────────────────────────────────────────${NC}"
        bash "$SCRIPT_DIR/runtimes/codex/install.sh"
        echo ""
        echo -e "${BOLD}── Claude Code ──────────────────────────────────────────────${NC}"
        bash "$SCRIPT_DIR/runtimes/claude-code/install.sh"
        ;;
    *)
        echo "Internal error: unknown mode '$mode'" >&2
        exit 2
        ;;
esac
