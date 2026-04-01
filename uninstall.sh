#!/usr/bin/env bash
# TrendR — 卸载脚本 v1.1.0

set -e

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"

echo "🗑️  卸载 TrendR..."
echo ""

# 删除核心 Agents
for agent in paper-scout paper-analyzer review-lead; do
    if [ -d "$WORKSPACE/agents/$agent" ]; then
        rm -rf "$WORKSPACE/agents/$agent"
        echo "  ✅ 移除 agents/$agent"
    fi
done

# 删除核心 Skills
for skill in paper-scout paper-analyzer review-writer research-vault trendr-watchdog; do
    if [ -d "$WORKSPACE/skills/$skill" ]; then
        rm -rf "$WORKSPACE/skills/$skill"
        echo "  ✅ 移除 skills/$skill"
    fi
done

# 删除 Full 模式专属 Skills（如果存在）
for skill in context7; do
    if [ -d "$WORKSPACE/skills/$skill" ]; then
        rm -rf "$WORKSPACE/skills/$skill"
        echo "  ✅ 移除 skills/$skill (Full 模式)"
    fi
done

# 删除配置文件
rm -f "$WORKSPACE/.trendr-config"

echo ""
echo "⚠️  以下需要手动操作："
echo "  1. 编辑 ~/.openclaw/workspace/AGENTS.md，删除 'TrendR' 部分"
echo "  2. 编辑 ~/.openclaw/openclaw.json，移除对应的 skills.entries 和 agents.list"
echo "  3. Obsidian vault 中的 Research/ 目录不会被删除（你的数据）"
echo "  4. ~/research/ 目录不会被删除（你的研究数据）"
echo "  5. 依赖 skills（arxiv-watcher、nano-pdf 等）不会被删除（其他功能可能在用）"
echo ""
echo "  openclaw gateway restart"
echo ""
