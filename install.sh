#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║  TrendR — Trend Research                                ║
# ║  自动化文献综述 + Obsidian 知识管理                        ║
# ║  3 Agents · 4 Skills · 9 源搜索 · 零额外 MCP 依赖        ║
# ╚══════════════════════════════════════════════════════════╝

set -e

VERSION="1.0.1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   TrendR v${VERSION} — Trend Research Installer   ║${NC}"
echo -e "${CYAN}║   自动化文献综述 + Obsidian 知识管理            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# Step 0: 检测环境
# ============================================================
echo -e "${BLUE}[0/8] 检测环境...${NC}"

ERRORS=0

# Node.js
if command -v node >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Node.js $(node --version)"
else
    echo -e "  ${RED}❌ Node.js 未安装${NC}"
    echo "     brew install node"
    ERRORS=$((ERRORS + 1))
fi

# npm / npx
if command -v npx >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} npx 可用"
else
    echo -e "  ${RED}❌ npx 未找到${NC}"
    ERRORS=$((ERRORS + 1))
fi

# OpenClaw
if command -v openclaw >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} OpenClaw $(openclaw --version 2>/dev/null || echo 'installed')"
else
    echo -e "  ${RED}❌ OpenClaw 未安装${NC}"
    echo "     npm install -g @anthropic-ai/openclaw"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo -e "${RED}请先安装上述缺失的依赖，然后重新运行本脚本。${NC}"
    exit 1
fi

# 检测 workspace 路径
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
if [ ! -d "$WORKSPACE" ]; then
    echo -e "  ${YELLOW}⚠️  workspace 不存在: $WORKSPACE${NC}"
    echo "     请先运行 'openclaw onboard' 完成初始化"
    exit 1
fi
echo -e "  ${GREEN}✅${NC} Workspace: $WORKSPACE"

# Obsidian Vault 路径 — 优先读 obsidian-cli 默认配置
if command -v obsidian-cli >/dev/null 2>&1; then
    DEFAULT_VAULT=$(obsidian-cli print-default 2>/dev/null | grep -i "path" | awk -F: '{print $2}' | xargs 2>/dev/null)
fi

if [ -n "$OBSIDIAN_VAULT" ]; then
    VAULT="$OBSIDIAN_VAULT"
elif [ -n "$DEFAULT_VAULT" ] && [ -d "$DEFAULT_VAULT" ]; then
    VAULT="$DEFAULT_VAULT"
    echo -e "  ${GREEN}✅${NC} 从 obsidian-cli 检测到默认 vault"
elif [ -d "$HOME/Documents/OpenClaw-Vault" ]; then
    VAULT="$HOME/Documents/OpenClaw-Vault"
elif [ -d "$HOME/Documents/ObsidianVault" ]; then
    VAULT="$HOME/Documents/ObsidianVault"
else
    echo ""
    echo -e "${YELLOW}未检测到 Obsidian Vault，请输入路径:${NC}"
    echo -e "  (直接回车使用默认: ~/Documents/OpenClaw-Vault)"
    read -r VAULT_INPUT
    VAULT="${VAULT_INPUT:-$HOME/Documents/OpenClaw-Vault}"
fi
echo -e "  ${GREEN}✅${NC} Vault: $VAULT"
echo ""

# ============================================================
# Step 1: 安装依赖 Skills + 二进制工具
# ============================================================
echo -e "${BLUE}[1/8] 安装依赖 Skills...${NC}"

SKILLS_TO_INSTALL=(
    "agent-browser"
    "obsidian"
    "deepresearchwork"
    "arxiv-watcher"
    "tavily-search"
    "playwright-mcp"
    "summarize"
)

for skill in "${SKILLS_TO_INSTALL[@]}"; do
    if [ -d "$WORKSPACE/skills/$skill" ] || [ -d "$HOME/.openclaw/skills/$skill" ]; then
        echo -e "  ${GREEN}✅${NC} $skill (已安装)"
    else
        echo -e "  ${CYAN}📦${NC} 安装 $skill..."
        npx clawhub@latest install "$skill" 2>/dev/null && \
            echo -e "  ${GREEN}✅${NC} $skill" || \
            echo -e "  ${YELLOW}⚠️  $skill 安装失败，可稍后手动: npx clawhub@latest install $skill${NC}"
    fi
done

# obsidian-cli（research-vault skill 依赖此二进制）
echo ""
echo -e "  ${BLUE}── 二进制依赖 ──${NC}"
if command -v obsidian-cli >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} obsidian-cli (已安装: $(which obsidian-cli))"
else
    echo -e "  ${CYAN}📦${NC} 安装 obsidian-cli..."
    brew tap yakitrak/yakitrak 2>/dev/null && \
    brew install obsidian-cli 2>/dev/null && \
        echo -e "  ${GREEN}✅${NC} obsidian-cli" || \
        echo -e "  ${YELLOW}⚠️  obsidian-cli 安装失败，手动运行:${NC}"
        echo -e "  ${YELLOW}   brew tap yakitrak/yakitrak && brew install obsidian-cli${NC}"
fi
echo ""

# ============================================================
# Step 2: 安装 Playwright 浏览器
# ============================================================
echo -e "${BLUE}[2/8] 检查 Playwright 浏览器...${NC}"

if command -v playwright-mcp >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} playwright-mcp 已安装"
else
    echo -e "  ${CYAN}📦${NC} 安装 playwright-mcp..."
    npm install -g @playwright/mcp 2>/dev/null || true
    npm install -g @playwright/test 2>/dev/null || true
    PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright" npx -g playwright install chromium 2>/dev/null || \
        echo -e "  ${YELLOW}⚠️  Chromium 安装失败，playwright-mcp 功能受限${NC}"
fi
echo ""

# ============================================================
# Step 3: 安装 TrendR Agents
# ============================================================
echo -e "${BLUE}[3/8] 安装 TrendR Agents...${NC}"

mkdir -p "$WORKSPACE/agents"
for agent in paper-scout paper-analyzer review-lead; do
    TARGET="$WORKSPACE/agents/$agent"
    if [ -d "$TARGET" ]; then
        echo -e "  ${YELLOW}⚠️${NC}  agents/$agent 已存在 — 备份并覆盖"
        cp -r "$TARGET" "${TARGET}.bak.$(date +%s)" 2>/dev/null || true
    fi
    cp -r "$SCRIPT_DIR/agents/$agent" "$WORKSPACE/agents/"
    echo -e "  ${GREEN}✅${NC} agents/$agent"
done
echo ""

# ============================================================
# Step 4: 安装 TrendR Skills
# ============================================================
echo -e "${BLUE}[4/8] 安装 TrendR Skills...${NC}"

mkdir -p "$WORKSPACE/skills"
for skill in paper-scout paper-analyzer review-writer research-vault; do
    TARGET="$WORKSPACE/skills/$skill"
    if [ -d "$TARGET" ]; then
        echo -e "  ${YELLOW}⚠️${NC}  skills/$skill 已存在 — 备份并覆盖"
        cp -r "$TARGET" "${TARGET}.bak.$(date +%s)" 2>/dev/null || true
    fi
    cp -r "$SCRIPT_DIR/skills/$skill" "$WORKSPACE/skills/"
    echo -e "  ${GREEN}✅${NC} skills/$skill"
done
echo ""

# ============================================================
# Step 5: 写入 Vault 路径配置
# ============================================================
echo -e "${BLUE}[5/8] 配置 Obsidian Vault 路径...${NC}"

VAULT_CONFIG="$WORKSPACE/.trendr-config"
cat > "$VAULT_CONFIG" << VEOF
# TrendR Configuration
# Generated: $(date -Iseconds)
OBSIDIAN_VAULT="$VAULT"
TRENDR_VERSION="$VERSION"
VEOF
echo -e "  ${GREEN}✅${NC} 路径已保存到 .trendr-config"

# 将 vault 路径注入 research-vault SKILL.md
sed -i '' "s|\~/Documents/OpenClaw-Vault|${VAULT}|g" "$WORKSPACE/skills/research-vault/SKILL.md" 2>/dev/null || \
sed -i "s|\~/Documents/OpenClaw-Vault|${VAULT}|g" "$WORKSPACE/skills/research-vault/SKILL.md" 2>/dev/null || true
echo -e "  ${GREEN}✅${NC} Vault 路径已注入 research-vault skill"
echo ""

# ============================================================
# Step 6: 初始化 Obsidian Vault 结构
# ============================================================
echo -e "${BLUE}[6/8] 初始化 Obsidian Vault 研究目录...${NC}"

mkdir -p "$VAULT/Research/"{_index,papers,reviews,daily,templates}

# 创建论文池索引
POOL="$VAULT/Research/_index/paper-pool.csv"
if [ ! -f "$POOL" ]; then
    echo "paper_id,title,authors,year,venue,source,citation_count,doi,project,added_date,tags,status" > "$POOL"
    echo -e "  ${GREEN}✅${NC} 论文池索引已创建"
else
    TOTAL=$(tail -n +2 "$POOL" | wc -l | tr -d ' ')
    echo -e "  ${GREEN}✅${NC} 论文池已存在 ($TOTAL 篇)"
fi

# 创建论文卡片模板
cat > "$VAULT/Research/templates/paper-card.md" << 'TEOF'
---
paper_id: "{{paper_id}}"
title: "{{title}}"
authors: {{authors}}
year: {{year}}
venue: "{{venue}}"
citations: {{citations}}
project: "{{project}}"
tags: {{tags}}
status: analyzed
created: {{date}}
---

# {{title}}

> **来源**: [[reviews/{{project}}/review|{{project}} 综述]]
> **论文池**: [[_index/paper-pool|论文池索引]]

## 研究问题
{{problem}}

## 方法
{{method}}

## 关键结果
{{results}}

## 主要贡献
{{contributions}}

## 局限性
{{limitations}}

## BibTeX
{{bibtex}}
TEOF

# 创建每日日志模板
cat > "$VAULT/Research/templates/daily-research.md" << 'TEOF'
---
date: {{date}}
projects: []
papers_found: 0
papers_analyzed: 0
---

# 研究日志 {{date}}

## 今日进展
-

## 值得关注的论文
-

## 明日计划
-
TEOF

echo -e "  ${GREEN}✅${NC} Obsidian 模板已创建"

# 测试 Obsidian 写入
if command -v obsidian-cli >/dev/null 2>&1; then
    VAULT_NAME=$(basename "$VAULT")
    obsidian-cli create "trendr-install-test" --vault "$VAULT_NAME" --content "# TrendR Install Test $(date)" 2>/dev/null && \
        echo -e "  ${GREEN}✅${NC} Obsidian 写入测试通过" && \
        rm -f "$VAULT/trendr-install-test.md" 2>/dev/null || \
        echo -e "  ${YELLOW}⚠️  Obsidian 写入测试失败，请确认: obsidian-cli set-default --vault $VAULT_NAME${NC}"
else
    echo -e "  ${YELLOW}⚠️  obsidian-cli 未安装，跳过写入测试${NC}"
fi

# 同步已有研究数据
if [ -d "$HOME/research" ]; then
    SYNCED=0
    for CAND in "$HOME"/research/*/candidates.csv; do
        [ -f "$CAND" ] || continue
        PROJECT=$(basename "$(dirname "$CAND")")
        BEFORE=$(tail -n +2 "$POOL" | wc -l | tr -d ' ')
        tail -n +2 "$CAND" 2>/dev/null | while IFS=, read -r pid _rest; do
            [ -n "$pid" ] && ! grep -q "^$pid," "$POOL" 2>/dev/null && \
                echo "$pid,$_rest,,,$PROJECT,$(date +%Y-%m-%d),,candidate" >> "$POOL"
        done
        AFTER=$(tail -n +2 "$POOL" | wc -l | tr -d ' ')
        ADDED=$((AFTER - BEFORE))
        [ "$ADDED" -gt 0 ] && echo -e "  ${GREEN}✅${NC} 同步 $PROJECT: +$ADDED 篇" && SYNCED=$((SYNCED + ADDED))
    done
    [ "$SYNCED" -gt 0 ] && echo -e "  ${GREEN}✅${NC} 已同步 $SYNCED 篇历史论文到池中"
fi
echo ""

# ============================================================
# Step 7: 更新 AGENTS.md
# ============================================================
echo -e "${BLUE}[7/8] 更新 AGENTS.md...${NC}"

if grep -q "TrendR" "$WORKSPACE/AGENTS.md" 2>/dev/null; then
    echo -e "  ${YELLOW}⚠️${NC}  AGENTS.md 已包含 TrendR 模块，跳过"
else
    cat >> "$WORKSPACE/AGENTS.md" << AGENTSEOF


---

## 📚 TrendR — 自动化文献综述

当用户要求调研某个学术主题或写文献综述时，启动 TrendR 工作流。

### 触发词
- "帮我调研..."、"文献综述"、"literature review"、"最新进展"
- "综述一下"、"搜索论文"、"survey"、"research review"

### 工作流

**Phase 1 — 论文搜索**
\`\`\`
exec: mkdir -p ~/research/[PROJECT]/{papers,notes}
\`\`\`
然后 sessions_spawn → paper-scout：
\`\`\`
sessions_spawn: {
  task: "先读 skills/paper-scout/SKILL.md，然后搜索以下主题，根据领域选 3-5 个最相关的源：\n[queries]\n项目路径: ~/research/[PROJECT]/",
  agentId: "paper-scout",
  mode: "run",
  runTimeoutSeconds: 300
}
\`\`\`

**Phase 2 — 论文精读**
读 candidates.csv，选 relevance_score >= 4，sessions_spawn → paper-analyzer：
\`\`\`
sessions_spawn: {
  task: "先读 skills/paper-analyzer/SKILL.md，分析以下论文：\n[paper_ids]\n项目路径: ~/research/[PROJECT]/",
  agentId: "paper-analyzer",
  mode: "run",
  runTimeoutSeconds: 600
}
\`\`\`

**Phase 3 — 空白检测**
读 notes + matrix.csv → 有空白回 Phase 1 → 充分进 Phase 4

**Phase 4 — 撰写综述**
先读 \`skills/review-writer/SKILL.md\`，自己写 review.md + references.bib

**Phase 5 — 持久化到 Obsidian（自动执行）**
先读 \`skills/research-vault/SKILL.md\`，然后：
1. 同步 candidates.csv → Obsidian 论文池（去重）
2. 转换 notes → Obsidian 论文卡片（带 wiki-link）
3. 归档 review.md + refs.bib → Obsidian reviews/
4. 写每日研究日志 → Obsidian daily/
⚠️ 这一步必须执行，不可跳过。所有研究成果都要持久化到 Obsidian。

**Phase 6 — 汇报**
通知用户完成，附关键发现摘要。

### 输出位置
\`\`\`
~/research/[PROJECT]/           ← 临时（用完可清理）
Obsidian/Research/              ← 永久知识库
  _index/paper-pool.csv         ← 论文池（累积）
  papers/[id].md                ← 论文卡片
  reviews/[project]/            ← 综述归档
  daily/[date].md               ← 日志
\`\`\`

### ⚠️ Vault 配置
首次使用前确认 obsidian-cli 已设置默认 vault：
  obsidian-cli set-default --vault $(basename "$VAULT")
  obsidian-cli print-default
默认写入 $(basename "$VAULT")。用户说"写到个人 vault"时才写其他 vault。

### ⚠️ 防遗忘规则
派发 subagent 时，任务描述中**必须**包含 "先读 skills/xxx/SKILL.md"。
不写这句话 = 任务大概率失败。

### 论文检索
用户说"查论文"/"找之前的论文"/"论文池"时：
\`\`\`bash
exec: grep -i "[关键词]" "${VAULT}/Research/_index/paper-pool.csv"
\`\`\`
有详细分析的论文引导用户到 Obsidian 查看。

AGENTSEOF
    echo -e "  ${GREEN}✅${NC} AGENTS.md 已追加 TrendR 工作流"
fi
echo ""

# ============================================================
# Step 8: 验证所有 Skills 和依赖状态
# ============================================================
echo -e "${BLUE}[8/8] 验证 Skills 和依赖状态...${NC}"
echo ""

DEP_FAIL=0

# ---- 7 个依赖 skill ----
echo -e "  ${BLUE}── 7 个依赖 Skills ──${NC}"
DEP_SKILLS=("arxiv-watcher" "tavily-search" "summarize" "deepresearchwork" "playwright-mcp" "agent-browser" "obsidian")
for skill in "${DEP_SKILLS[@]}"; do
    if [ -d "$WORKSPACE/skills/$skill" ] || [ -d "$HOME/.openclaw/skills/$skill" ]; then
        echo -e "  ${GREEN}✅${NC} $skill"
    else
        echo -e "  ${RED}❌${NC} $skill — 未安装"
        echo -e "     ${YELLOW}运行: npx clawhub@latest install $skill${NC}"
        DEP_FAIL=$((DEP_FAIL + 1))
    fi
done

echo ""

# ---- 4 个 TrendR skill ----
echo -e "  ${BLUE}── 4 个 TrendR Skills ──${NC}"
TRENDR_SKILLS=("paper-scout" "paper-analyzer" "review-writer" "research-vault")
for skill in "${TRENDR_SKILLS[@]}"; do
    if [ -d "$WORKSPACE/skills/$skill" ]; then
        echo -e "  ${GREEN}✅${NC} $skill (TrendR)"
    else
        echo -e "  ${RED}❌${NC} $skill — 缺失 (TrendR 安装异常)"
        DEP_FAIL=$((DEP_FAIL + 1))
    fi
done

echo ""

# ---- 二进制依赖（决定 skill eligible/blocked）----
echo -e "  ${BLUE}── 二进制依赖（影响 eligible/blocked 状态）──${NC}"

if command -v obsidian-cli >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} obsidian-cli → research-vault skill = eligible"
else
    echo -e "  ${RED}❌${NC} obsidian-cli → research-vault skill = ${RED}blocked${NC}"
    echo -e "     ${YELLOW}运行: brew tap yakitrak/yakitrak && brew install obsidian-cli${NC}"
    DEP_FAIL=$((DEP_FAIL + 1))
fi

if command -v playwright-mcp >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} playwright-mcp → playwright-mcp skill = eligible"
else
    echo -e "  ${RED}❌${NC} playwright-mcp → playwright-mcp skill = ${RED}blocked${NC}"
    echo -e "     ${YELLOW}运行: npm install -g @playwright/mcp${NC}"
    DEP_FAIL=$((DEP_FAIL + 1))
fi

echo ""

# ---- 结果汇总 ----
if [ "$DEP_FAIL" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠️  有 $DEP_FAIL 项需要手动处理（见上方 ❌ 标记）${NC}"
    echo -e "  ${YELLOW}   处理完后运行: openclaw gateway restart${NC}"
else
    echo -e "  ${GREEN}✅ 全部 11 个 Skills 就绪，2 个二进制依赖已安装！${NC}"
fi
echo ""

# ============================================================
# 完成
# ============================================================
POOL_COUNT=$(tail -n +2 "$POOL" 2>/dev/null | wc -l | tr -d ' ')

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          TrendR v${VERSION} 安装完成！              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}Agents${NC}:   paper-scout, paper-analyzer, review-lead"
echo -e "  ${GREEN}Skills${NC}:   paper-scout (9源), paper-analyzer, review-writer, research-vault"
echo -e "  ${GREEN}Vault${NC}:    $VAULT/Research/"
echo -e "  ${GREEN}论文池${NC}:   $POOL_COUNT 篇"
echo ""
echo -e "  ${BLUE}下一步:${NC}"
echo "  1. 确认 obsidian-cli 默认 vault:"
echo "     obsidian-cli set-default --vault $(basename "$VAULT")"
echo "  2. 确认 openclaw.json 中 agents.list 和 skills.entries 已配置"
echo "  3. openclaw gateway restart"
echo "  4. 对你的 Agent 说: '帮我调研 XXX 方向的最新进展'"
echo ""
echo -e "  ${BLUE}卸载:${NC}"
echo "  chmod +x $(dirname "$0")/uninstall.sh && $(dirname "$0")/uninstall.sh"
echo ""
