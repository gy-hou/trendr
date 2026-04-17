#!/usr/bin/env bash
# TrendR — Claude Code Installer
# Installs TrendR agents, commands, and plugin manifest for Claude Code.

set -e

# SCRIPT_DIR points to repo root (two levels up from runtimes/claude-code/)
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
scope="${scope:-project}"
DRY_RUN="${DRY_RUN:-0}"
FORCE=0

# ── colors ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
DIM='\033[2m'

# ── parse flags ─────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)      scope="user";  shift ;;
        --project)   scope="project"; shift ;;
        --dry-run)   DRY_RUN=1;    shift ;;
        --force)     FORCE=1;      shift ;;
        -h|--help)
            echo "Usage: runtimes/claude-code/install.sh [--user|--project] [--dry-run] [--force]"
            echo ""
            echo "  --user      install into ~/.claude/ (global scope)"
            echo "  --project   install into <repo>/.claude/ (default)"
            echo "  --dry-run   list actions without executing them"
            echo "  --force     skip claude CLI check"
            exit 0 ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

# ── dry-run helper ───────────────────────────────────────────────
_do() {
    if [ "$DRY_RUN" = "1" ]; then
        echo -e "  ${DIM}[dry-run] $*${NC}"
    else
        eval "$@"
    fi
}

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║         TrendR — Claude Code Installer                       ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Scope:${NC}   $scope"
echo -e "  ${BOLD}Repo:${NC}    $SCRIPT_DIR"
[ "$DRY_RUN" = "1" ] && echo -e "  ${YELLOW}DRY RUN — no changes will be made${NC}"
echo ""

# ══════════════════════════════════════════════════════════════════
# 1. Check claude CLI
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[1/5] Checking claude CLI...${NC}"
if command -v claude >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} claude CLI found: $(command -v claude)"
else
    if [ "$FORCE" = "1" ]; then
        echo -e "  ${YELLOW}⚠️${NC}  claude CLI not found — continuing with --force"
    else
        echo -e "  ${RED}❌${NC} claude CLI not found in PATH"
        echo ""
        echo "  Install Claude Code:"
        echo "    npm install -g @anthropic-ai/claude-code"
        echo "  or visit: https://claude.ai/code"
        echo ""
        echo "  Re-run with --force to skip this check."
        exit 1
    fi
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 2. Validate authority sources
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[2/5] Validating authority sources...${NC}"
ERRORS=0

_check_path() {
    local label="$1" path="$2"
    if [ -e "$path" ]; then
        echo -e "  ${GREEN}✅${NC} $label"
    else
        echo -e "  ${RED}❌${NC} $label — not found: $path"
        ERRORS=$((ERRORS+1))
    fi
}

for agent in paper-scout paper-analyzer review-lead verifier; do
    _check_path "agents/$agent/claude-code.md" "$SCRIPT_DIR/agents/$agent/claude-code.md"
done
_check_path "runtimes/claude-code/commands/" "$SCRIPT_DIR/runtimes/claude-code/commands"
_check_path "runtimes/claude-code/plugin.json" "$SCRIPT_DIR/runtimes/claude-code/plugin.json"
_check_path "runtimes/claude-code/render-commands.sh" "$SCRIPT_DIR/runtimes/claude-code/render-commands.sh"

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo -e "${RED}Authority sources missing. Is this a complete TrendR checkout?${NC}"
    exit 1
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 3. Determine target directory
# ══════════════════════════════════════════════════════════════════
if [ "$scope" = "user" ]; then
    target="$HOME"
else
    target="$SCRIPT_DIR"
fi

AGENTS_DIR="$target/.claude/agents"
COMMANDS_DIR="$target/.claude/commands"
PLUGIN_DIR="$target/.claude-plugin"

# ══════════════════════════════════════════════════════════════════
# 4. Install agents as symlinks (fallback to cp)
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[3/5] Installing agent stubs...${NC}"
_do "mkdir -p \"$AGENTS_DIR\""

for agent in paper-scout paper-analyzer review-lead verifier; do
    src="$SCRIPT_DIR/agents/$agent/claude-code.md"
    dst="$AGENTS_DIR/$agent.md"
    if [ "$DRY_RUN" = "1" ]; then
        echo -e "  ${DIM}[dry-run] symlink $src -> $dst${NC}"
    else
        # Remove stale link/file first
        rm -f "$dst"
        if ln -sf "$src" "$dst" 2>/dev/null; then
            echo -e "  ${GREEN}✅${NC} .claude/agents/$agent.md -> agents/$agent/claude-code.md (symlink)"
        else
            cp "$src" "$dst"
            echo -e "  ${GREEN}✅${NC} .claude/agents/$agent.md (copied — symlink not supported)"
        fi
    fi
done
echo ""

# ══════════════════════════════════════════════════════════════════
# 5. Render commands
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[4/5] Rendering commands...${NC}"
if [ "$DRY_RUN" = "1" ]; then
    echo -e "  ${DIM}[dry-run] bash runtimes/claude-code/render-commands.sh --dst \"$COMMANDS_DIR\" --repo-root \"$SCRIPT_DIR\"${NC}"
else
    bash "$SCRIPT_DIR/runtimes/claude-code/render-commands.sh" \
        --dst "$COMMANDS_DIR" \
        --repo-root "$SCRIPT_DIR"
    echo -e "  ${GREEN}✅${NC} commands rendered to .claude/commands/"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 6. plugin.json symlink
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[5/5] Installing plugin manifest...${NC}"
plugin_src="$SCRIPT_DIR/runtimes/claude-code/plugin.json"
plugin_dst="$PLUGIN_DIR/plugin.json"

if [ "$DRY_RUN" = "1" ]; then
    echo -e "  ${DIM}[dry-run] mkdir -p $PLUGIN_DIR${NC}"
    echo -e "  ${DIM}[dry-run] symlink $plugin_src -> $plugin_dst${NC}"
else
    mkdir -p "$PLUGIN_DIR"
    rm -f "$plugin_dst"
    if ln -sf "$plugin_src" "$plugin_dst" 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} .claude-plugin/plugin.json -> runtimes/claude-code/plugin.json (symlink)"
    else
        cp "$plugin_src" "$plugin_dst"
        echo -e "  ${GREEN}✅${NC} .claude-plugin/plugin.json (copied — symlink not supported)"
    fi
fi

# ── user scope: also create ~/.claude/plugins/trendr/ symlink ──
if [ "$scope" = "user" ]; then
    plugins_link="$HOME/.claude/plugins/trendr"
    if [ "$DRY_RUN" = "1" ]; then
        echo -e "  ${DIM}[dry-run] symlink $SCRIPT_DIR -> $plugins_link${NC}"
    else
        mkdir -p "$HOME/.claude/plugins"
        rm -f "$plugins_link"
        if ln -sf "$SCRIPT_DIR" "$plugins_link" 2>/dev/null; then
            echo -e "  ${GREEN}✅${NC} ~/.claude/plugins/trendr -> $SCRIPT_DIR (symlink)"
        else
            echo -e "  ${YELLOW}⚠️${NC}  Could not create ~/.claude/plugins/trendr symlink (not fatal)"
        fi
    fi
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Merge hooks into settings.json
# ══════════════════════════════════════════════════════════════════
SETTINGS_FILE="$HOME/.claude/settings.json"
PLUGIN_ROOT="$SCRIPT_DIR/runtimes/claude-code"

_merge_hooks() {
    python3 - "$SETTINGS_FILE" "$PLUGIN_ROOT" << 'PYEOF'
import json, sys, os

settings_path = sys.argv[1]
plugin_root = sys.argv[2]

trendr_hooks = {
    "trendr_session_start": {
        "event": "SessionStart",
        "command": f"python \"{plugin_root}/hooks/session_start.py\""
    },
    "trendr_stop_heartbeat": {
        "event": "Stop",
        "command": f"python \"{plugin_root}/hooks/stop_heartbeat.py\""
    },
    "trendr_subagent_stop": {
        "event": "SubagentStop",
        "command": f"python \"{plugin_root}/hooks/subagent_stop.py\""
    }
}

# Read existing settings
if os.path.exists(settings_path):
    with open(settings_path) as f:
        try:
            settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
else:
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    settings = {}

hooks = settings.setdefault("hooks", {})
added = []
skipped = []

for key, val in trendr_hooks.items():
    if key not in hooks:
        hooks[key] = val
        added.append(key)
    else:
        skipped.append(key)

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

for k in added:
    print(f"  added hook: {k}")
for k in skipped:
    print(f"  hook already present (not overwritten): {k}")
PYEOF
}

if [ "$DRY_RUN" = "1" ]; then
    echo -e "  ${DIM}[dry-run] merge trendr hooks into ~/.claude/settings.json${NC}"
else
    echo -e "  Merging hooks into ~/.claude/settings.json..."
    _merge_hooks
    echo -e "  ${GREEN}✅${NC} hooks merged"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║         TrendR Claude Code install done!                     ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Agents installed:${NC}  paper-scout · paper-analyzer · review-lead · verifier"
echo -e "  ${BOLD}Commands:${NC}          /tr · /tr/research · /tr/hotspots · /tr/status · /tr/resume · /tr/template"
echo -e "  ${BOLD}Plugin manifest:${NC}   .claude-plugin/plugin.json"
echo ""
echo -e "  ${BOLD}Usage examples:${NC}"
echo "    /tr research \"agentic RAG 2025\""
echo "    /tr hotspots"
echo "    /tr status"
echo "    /tr resume"
echo ""
echo -e "  ${DIM}To uninstall: bash runtimes/claude-code/uninstall.sh${NC}"
echo ""
