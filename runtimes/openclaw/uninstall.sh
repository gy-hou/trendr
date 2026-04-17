#!/usr/bin/env bash
# TrendR — OpenClaw 卸载脚本 v1.1.0

set -e

# SCRIPT_DIR points to repo root (two levels up from runtimes/openclaw/)
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"

echo "  卸载 TrendR (OpenClaw runtime)..."
echo ""

# 删除核心 Agents
for agent in paper-scout paper-analyzer review-lead verifier; do
    if [ -d "$WORKSPACE/agents/$agent" ]; then
        rm -rf "$WORKSPACE/agents/$agent"
        echo "  removed agents/$agent"
    fi
done

# 删除核心 Skills
for skill in paper-scout paper-analyzer review-writer verifier research-vault trendr-watchdog chrome-cdp-setup platform-hotspots; do
    if [ -d "$WORKSPACE/skills/$skill" ]; then
        rm -rf "$WORKSPACE/skills/$skill"
        echo "  removed skills/$skill"
    fi
done

# 删除 Full 模式专属 Skills（如果存在）
for skill in context7 nano-pdf; do
    if [ -d "$WORKSPACE/skills/$skill" ]; then
        rm -rf "$WORKSPACE/skills/$skill"
        echo "  removed skills/$skill (Full mode)"
    fi
done

# 删除 engine（如果是从仓库复制过去的）
if [ -d "$WORKSPACE/engine" ]; then
    rm -rf "$WORKSPACE/engine"
    echo "  removed engine/"
fi

# 删除配置文件
rm -f "$WORKSPACE/.trendr-config"

echo ""
echo "  The following require manual action:"
echo "  1. Edit ~/.openclaw/workspace/AGENTS.md and remove the 'TrendR' section"
echo "  2. Edit ~/.openclaw/openclaw.json and remove skills.entries and agents.list entries for TrendR"
echo "  3. Obsidian vault Research/ directory is NOT deleted (your data)"
echo "  4. ~/research/ directory is NOT deleted (your research data)"
echo "  5. Dependency skills (arxiv-watcher, nano-pdf, etc.) are NOT deleted"
echo ""
echo "  openclaw gateway restart"
echo ""
