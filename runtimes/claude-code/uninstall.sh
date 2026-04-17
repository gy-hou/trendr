#!/usr/bin/env bash
# TrendR — Claude Code Uninstaller
# Removes TrendR agents, commands, plugin manifest, and hooks installed for Claude Code.

set -e

# SCRIPT_DIR points to repo root (two levels up from runtimes/claude-code/)
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
scope="${scope:-project}"
DRY_RUN="${DRY_RUN:-0}"

# ── colors ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
DIM='\033[2m'

# ── parse flags ─────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)    scope="user";    shift ;;
        --project) scope="project"; shift ;;
        --dry-run) DRY_RUN=1;      shift ;;
        -h|--help)
            echo "Usage: runtimes/claude-code/uninstall.sh [--user|--project] [--dry-run]"
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

if [ "$scope" = "user" ]; then
    target="$HOME"
else
    target="$SCRIPT_DIR"
fi

echo ""
echo -e "${CYAN}${BOLD}TrendR — Claude Code Uninstall${NC}"
echo ""
[ "$DRY_RUN" = "1" ] && echo -e "  ${YELLOW}DRY RUN — no changes will be made${NC}" && echo ""

REMOVED=0
SKIPPED=0

# ══════════════════════════════════════════════════════════════════
# 1. Remove agent stubs (only our symlinks / our copies)
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[1/4] Removing agent stubs...${NC}"
AGENTS_DIR="$target/.claude/agents"

for agent in paper-scout paper-analyzer review-lead verifier; do
    dst="$AGENTS_DIR/$agent.md"
    if [ ! -e "$dst" ] && [ ! -L "$dst" ]; then
        echo -e "  ${DIM}skip $dst (not found)${NC}"
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    # Only remove if it's our symlink or a copy of our file
    our_src="$SCRIPT_DIR/agents/$agent/claude-code.md"
    is_ours=false

    if [ -L "$dst" ]; then
        link_target="$(readlink "$dst" 2>/dev/null || true)"
        if [ "$link_target" = "$our_src" ]; then
            is_ours=true
        fi
    elif [ -f "$dst" ] && [ -f "$our_src" ]; then
        if diff -q "$dst" "$our_src" >/dev/null 2>&1; then
            is_ours=true
        fi
    fi

    if [ "$is_ours" = "true" ]; then
        _do "rm -f \"$dst\""
        echo -e "  ${GREEN}✅${NC} removed .claude/agents/$agent.md"
        REMOVED=$((REMOVED+1))
    else
        echo -e "  ${YELLOW}skip${NC} .claude/agents/$agent.md (not ours — leaving intact)"
        SKIPPED=$((SKIPPED+1))
    fi
done
echo ""

# ══════════════════════════════════════════════════════════════════
# 2. Remove rendered commands (tr*)
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[2/4] Removing commands...${NC}"
COMMANDS_DIR="$target/.claude/commands"

# Remove top-level tr.md
if [ -e "$COMMANDS_DIR/tr.md" ] || [ -L "$COMMANDS_DIR/tr.md" ]; then
    _do "rm -f \"$COMMANDS_DIR/tr.md\""
    echo -e "  ${GREEN}✅${NC} removed .claude/commands/tr.md"
    REMOVED=$((REMOVED+1))
fi

# Remove tr/ subdirectory
if [ -d "$COMMANDS_DIR/tr" ]; then
    _do "rm -rf \"$COMMANDS_DIR/tr\""
    echo -e "  ${GREEN}✅${NC} removed .claude/commands/tr/"
    REMOVED=$((REMOVED+1))
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 3. Remove plugin.json symlink
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[3/4] Removing plugin manifest...${NC}"
PLUGIN_DIR="$target/.claude-plugin"
plugin_dst="$PLUGIN_DIR/plugin.json"
plugin_src="$SCRIPT_DIR/runtimes/claude-code/plugin.json"

if [ -L "$plugin_dst" ]; then
    link_target="$(readlink "$plugin_dst" 2>/dev/null || true)"
    if [ "$link_target" = "$plugin_src" ]; then
        _do "rm -f \"$plugin_dst\""
        echo -e "  ${GREEN}✅${NC} removed .claude-plugin/plugin.json symlink"
        REMOVED=$((REMOVED+1))
        # Remove dir if now empty
        if [ "$DRY_RUN" != "1" ] && [ -d "$PLUGIN_DIR" ] && [ -z "$(ls -A "$PLUGIN_DIR" 2>/dev/null)" ]; then
            rmdir "$PLUGIN_DIR" 2>/dev/null || true
        fi
    else
        echo -e "  ${YELLOW}skip${NC} .claude-plugin/plugin.json (points elsewhere — leaving intact)"
        SKIPPED=$((SKIPPED+1))
    fi
elif [ -e "$plugin_dst" ]; then
    echo -e "  ${YELLOW}skip${NC} .claude-plugin/plugin.json (not our symlink — leaving intact)"
    SKIPPED=$((SKIPPED+1))
fi

# user scope: remove ~/.claude/plugins/trendr/ symlink
if [ "$scope" = "user" ]; then
    plugins_link="$HOME/.claude/plugins/trendr"
    if [ -L "$plugins_link" ]; then
        _do "rm -f \"$plugins_link\""
        echo -e "  ${GREEN}✅${NC} removed ~/.claude/plugins/trendr symlink"
        REMOVED=$((REMOVED+1))
    fi
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 4. Remove trendr hooks from ~/.claude/settings.json
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[4/4] Removing hooks from settings.json...${NC}"
SETTINGS_FILE="$HOME/.claude/settings.json"

_remove_hooks() {
    python3 - "$SETTINGS_FILE" << 'PYEOF'
import json, sys, os

settings_path = sys.argv[1]
if not os.path.exists(settings_path):
    print("  settings.json not found — nothing to do")
    sys.exit(0)

with open(settings_path) as f:
    try:
        settings = json.load(f)
    except json.JSONDecodeError:
        print("  settings.json is not valid JSON — skipping hook removal")
        sys.exit(0)

hooks = settings.get("hooks", {})
removed = [k for k in list(hooks.keys()) if k.startswith("trendr_")]
for k in removed:
    del hooks[k]

if removed:
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    for k in removed:
        print(f"  removed hook: {k}")
else:
    print("  no trendr hooks found in settings.json")
PYEOF
}

if [ "$DRY_RUN" = "1" ]; then
    echo -e "  ${DIM}[dry-run] remove trendr_* hooks from ~/.claude/settings.json${NC}"
else
    _remove_hooks
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════
echo -e "${CYAN}${BOLD}Uninstall complete.${NC}"
echo ""
echo -e "  Removed: $REMOVED item(s)"
echo -e "  Skipped: $SKIPPED item(s) (not ours or already absent)"
echo ""
echo -e "  ${DIM}The runtimes/claude-code/ directory (repo content) is NOT removed.${NC}"
echo -e "  ${DIM}OpenClaw directories are NOT touched.${NC}"
echo ""
