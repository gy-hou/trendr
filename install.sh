#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║  TrendR — Trend Research Installer                              ║
# ║  自动化文献综述 · 9 源搜索 · Obsidian 知识管理                    ║
# ║  版本: 1.1.1                                                    ║
# ╚══════════════════════════════════════════════════════════════════╝

set -e
VERSION="1.1.1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 颜色 ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
DIM='\033[2m'

# ══════════════════════════════════════════════════════════════════
# 0.  WHAT YOU'RE ABOUT TO INSTALL（安装前必读，不跳过）
# ══════════════════════════════════════════════════════════════════
clear
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║            TrendR v${VERSION} — 安装前说明                       ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}TrendR 是什么？${NC}"
echo "  一套跑在 OpenClaw 里的自动化文献调研工作流："
echo "  搜论文 → 去重评分 → 精读提取 → 生成综述 → 知识库持久化"
echo ""
echo -e "${BOLD}TrendR 会安装哪些东西？${NC}"
echo ""
echo -e "  ${GREEN}▸ 核心 Agents（3 个，必装）${NC}"
echo -e "    ${DIM}paper-scout     多源学术论文搜索与评分${NC}"
echo -e "    ${DIM}paper-analyzer  论文精读、结构化笔记、对比矩阵${NC}"
echo -e "    ${DIM}review-lead     综述撰写、质量审查${NC}"
echo ""
echo -e "  ${GREEN}▸ 核心 Skills（5 个，必装）${NC}"
echo -e "    ${DIM}paper-scout     9 源学术 API 搜索命令手册${NC}"
echo -e "    ${DIM}paper-analyzer  结构化提取模板${NC}"
echo -e "    ${DIM}review-writer   综述撰写模板 + BibTeX 生成${NC}"
echo -e "    ${DIM}research-vault  Obsidian 持久化协议${NC}"
echo -e "    ${DIM}trendr-watchdog 运行时监督 + 超时自动续接${NC}"
echo ""
echo -e "  ${BLUE}▸ 主链搜索栈（Basic 模式即可运行）${NC}"
echo -e "    ${DIM}9-source APIs   arXiv / Semantic Scholar / OpenAlex / PubMed /${NC}"
echo -e "    ${DIM}                CrossRef / DBLP / Europe PMC / bioRxiv / Papers with Code${NC}"
echo -e "    ${DIM}                ── 全部通过 web_fetch 调用，零额外依赖 ──${NC}"
echo ""
echo -e "  ${CYAN}▸ 增强层（Full 模式专属，可选）${NC}"
echo ""
echo -e "    ${BOLD}[Scrapling]${NC}  ${DIM}深挖模式爬取 —— 提取 JS 渲染后的页面内容${NC}"
echo -e "    ${DIM}             依赖: Python 3 + pip install scrapling${NC}"
echo -e "    ${DIM}             关掉: 仅用静态 API 搜索，覆盖率略低${NC}"
echo ""
echo -e "    ${BOLD}[Zotero]${NC}     ${DIM}文献管理同步 —— 自动导入 DOI、管理引用库${NC}"
echo -e "    ${DIM}             依赖: Zotero 桌面 App + API Key${NC}"
echo -e "    ${DIM}             关掉: 无法自动同步到 Zotero，BibTeX 仍可本地生成${NC}"
echo ""
echo -e "    ${BOLD}[Obsidian]${NC}   ${DIM}知识库持久化 —— 论文卡片 + 综述归档 + 每日日志${NC}"
echo -e "    ${DIM}             依赖: Obsidian App + obsidian-cli (brew)${NC}"
echo -e "    ${DIM}             关掉: 结果只存本地 ~/research/，不进 Obsidian${NC}"
echo ""
echo -e "    ${BOLD}[Nano-pdf]${NC}   ${DIM}PDF 处理 —— 精读全文 PDF 而不只是摘要${NC}"
echo -e "    ${DIM}             依赖: nano-pdf CLI (通过 OpenClaw 安装)${NC}"
echo -e "    ${DIM}             关掉: 只读摘要/元数据，不读 PDF 全文${NC}"
echo ""
echo -e "    ${BOLD}[Context7]${NC}   ${DIM}文档增强 —— 给 codex-coder 提供精确库文档${NC}"
echo -e "    ${DIM}             依赖: npx @upstash/context7-mcp（首次自动下载）${NC}"
echo -e "    ${DIM}             关掉: coding/config 任务退回 web search${NC}"
echo ""
echo -e "  ${YELLOW}▸ 回退层（两种模式都不默认启用）${NC}"
echo ""
echo -e "    ${BOLD}[Playwright]${NC} ${DIM}浏览器自动化 —— 仅在以下情况才启用：${NC}"
echo -e "    ${DIM}             · 页面 JS 渲染导致内容缺失${NC}"
echo -e "    ${DIM}             · 连续 2 次抽取为空或明显不完整${NC}"
echo -e "    ${DIM}             · 需要登录态 / 验证码 / 交互式表单${NC}"
echo -e "    ${DIM}             · 用户明确要求操作 live webpage${NC}"
echo -e "    ${DIM}             依赖: npm install -g @playwright/mcp + Chromium${NC}"
echo -e "    ${DIM}             策略: 不进默认检索链；Full 模式可选安装${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}版本对比：${NC}"
echo ""
printf "  %-30s %-12s %-12s\n" "功能" "Basic" "Full"
printf "  %-30s %-12s %-12s\n" "──────────────────────────────" "──────────" "──────────"
printf "  %-30s ${GREEN}%-12s${NC} ${GREEN}%-12s${NC}\n" "9 源学术 API 搜索"           "✅ 包含" "✅ 包含"
printf "  %-30s ${GREEN}%-12s${NC} ${GREEN}%-12s${NC}\n" "论文评分 / 去重"             "✅ 包含" "✅ 包含"
printf "  %-30s ${GREEN}%-12s${NC} ${GREEN}%-12s${NC}\n" "精读 + 结构化笔记"           "✅ 包含" "✅ 包含"
printf "  %-30s ${GREEN}%-12s${NC} ${GREEN}%-12s${NC}\n" "文献综述 + BibTeX"           "✅ 包含" "✅ 包含"
printf "  %-30s ${GREEN}%-12s${NC} ${GREEN}%-12s${NC}\n" "arXiv 追踪 / 每日论文日报"   "✅ 包含" "✅ 包含"
printf "  %-30s ${YELLOW}%-12s${NC} ${GREEN}%-12s${NC}\n" "Scrapling 深挖爬取"         "⬜ 跳过" "✅ 安装"
printf "  %-30s ${YELLOW}%-12s${NC} ${GREEN}%-12s${NC}\n" "Zotero 文献库同步"          "⬜ 跳过" "✅ 配置"
printf "  %-30s ${YELLOW}%-12s${NC} ${GREEN}%-12s${NC}\n" "Obsidian 知识库持久化"      "⬜ 跳过" "✅ 安装"
printf "  %-30s ${YELLOW}%-12s${NC} ${GREEN}%-12s${NC}\n" "Nano-pdf 全文精读"          "⬜ 跳过" "✅ 安装"
printf "  %-30s ${YELLOW}%-12s${NC} ${GREEN}%-12s${NC}\n" "Context7 文档增强"          "⬜ 跳过" "✅ 安装"
printf "  %-30s ${RED}%-12s${NC} ${YELLOW}%-12s${NC}\n"  "Playwright 回退层"          "❌ 不装" "⚠️  可选"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}选择安装模式：${NC}"
echo ""
echo -e "  ${GREEN}[1] Basic${NC}  — 仅核心链路，立刻可用，无额外工具依赖"
echo -e "  ${CYAN}[2] Full${NC}   — 完整功能：主链 + Scrapling + Zotero + Obsidian + Nano-pdf + Context7"
echo -e "  ${RED}[q] 退出${NC}   — 先看看再说"
echo ""
printf "  请输入选项 [1/2/q]: "
read -r MODE_INPUT

case "$MODE_INPUT" in
    1) INSTALL_MODE="basic"  ;;
    2) INSTALL_MODE="full"   ;;
    q|Q) echo ""; echo -e "${YELLOW}已退出。需要时重新运行 install.sh。${NC}"; echo ""; exit 0 ;;
    *) echo -e "${RED}无效输入，请重新运行并输入 1、2 或 q。${NC}"; exit 1 ;;
esac

echo ""
if [ "$INSTALL_MODE" = "basic" ]; then
    echo -e "${GREEN}${BOLD}▶ 已选择 Basic 模式${NC}"
    echo -e "  ${DIM}安装核心链路（9 源搜索 + 论文分析 + 综述生成）${NC}"
    echo -e "  ${DIM}结果保存到 ~/research/<project>/（不写 Obsidian）${NC}"
else
    echo -e "${CYAN}${BOLD}▶ 已选择 Full 模式${NC}"
    echo -e "  ${DIM}安装完整功能（核心 + Scrapling + Zotero + Obsidian + Nano-pdf + Context7）${NC}"
fi
echo ""
printf "  确认继续？[y/N]: "
read -r CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "已取消。"; exit 0; }
echo ""

# ══════════════════════════════════════════════════════════════════
# 1.  环境检测
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[1/8] 检测基础环境...${NC}"
ERRORS=0

_check() {
    local label="$1" cmd="$2" fix="$3"
    if command -v "$cmd" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $label"
    else
        echo -e "  ${RED}❌${NC} $label — 未找到"
        [ -n "$fix" ] && echo -e "      ${DIM}修复: $fix${NC}"
        ERRORS=$((ERRORS+1))
    fi
}

_check "Node.js"  "node"      "brew install node"
_check "npx"      "npx"       "随 Node.js 附带"
_check "OpenClaw" "openclaw"  "参考 OpenClaw 官方文档安装"

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo -e "${RED}请先安装上述缺失依赖，然后重新运行。${NC}"
    exit 1
fi

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
if [ ! -d "$WORKSPACE" ]; then
    echo -e "  ${RED}❌ workspace 不存在: $WORKSPACE${NC}"
    echo -e "     ${DIM}请先运行: openclaw onboard${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅${NC} Workspace: $WORKSPACE"

# DNS fake-ip 预检（不阻断）
DNS_FAKE_IP=false
DNS_FAKE_IP_HITS=""
if command -v node >/dev/null 2>&1; then
    DNS_CHECK=$(node <<'NODE'
const dns = require("dns").promises;
const domains = ["export.arxiv.org", "api.semanticscholar.org", "api.openalex.org", "paperswithcode.com"];
function isFakeIp(ip) {
  const parts = ip.split(".");
  if (parts.length !== 4) return false;
  const a = Number(parts[0]);
  const b = Number(parts[1]);
  return Number.isFinite(a) && Number.isFinite(b) && a === 198 && (b === 18 || b === 19);
}
(async () => {
  const hits = [];
  for (const d of domains) {
    try {
      const rows = await dns.lookup(d, { all: true });
      for (const r of rows) {
        if (isFakeIp(r.address)) hits.push(`${d}=${r.address}`);
      }
    } catch {}
  }
  if (hits.length > 0) {
    console.log(`fakeip:${hits.join(",")}`);
  } else {
    console.log("ok");
  }
})();
NODE
)
    if [[ "$DNS_CHECK" == fakeip:* ]]; then
        DNS_FAKE_IP=true
        DNS_FAKE_IP_HITS="${DNS_CHECK#fakeip:}"
        echo -e "  ${YELLOW}⚠️${NC}  检测到 DNS Fake-IP（198.18.x.x）: ${DNS_FAKE_IP_HITS}"
        echo -e "     ${DIM}TrendR 会自动启用兜底检索，但学术 API 覆盖率可能下降${NC}"
    fi
fi

# Full 模式：预检额外依赖（只报告，不阻断）
SCRAPLING_OK=false; OBSIDIAN_OK=false; ZOTERO_OK=false

if [ "$INSTALL_MODE" = "full" ]; then
    echo ""
    echo -e "  ${DIM}── Full 模式额外依赖预检 ──${NC}"

    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "import scrapling" 2>/dev/null; then
            SCRAPLING_OK=true
            echo -e "  ${GREEN}✅${NC} scrapling（已安装）"
        else
            echo -e "  ${YELLOW}⚠️${NC}  scrapling 未安装（稍后自动: pip3 install scrapling）"
        fi
    else
        echo -e "  ${YELLOW}⚠️${NC}  Python 3 未找到，Scrapling 将跳过"
    fi

    if command -v obsidian-cli >/dev/null 2>&1; then
        OBSIDIAN_OK=true
        echo -e "  ${GREEN}✅${NC} obsidian-cli（已安装）"
    else
        echo -e "  ${YELLOW}⚠️${NC}  obsidian-cli 未安装（稍后自动: brew install obsidian-cli）"
    fi

    if [ -n "$ZOTERO_API_KEY" ] && [ -n "$ZOTERO_USER_ID" ]; then
        ZOTERO_OK=true
        echo -e "  ${GREEN}✅${NC} Zotero env vars 已设置"
    else
        echo -e "  ${YELLOW}⚠️${NC}  ZOTERO_API_KEY / ZOTERO_USER_ID 未设置（安装后手动配置）"
    fi
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 2.  Vault 路径配置
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[2/8] 配置输出路径...${NC}"
VAULT=""

if [ "$INSTALL_MODE" = "full" ]; then
    if command -v obsidian-cli >/dev/null 2>&1; then
        AUTO_VAULT=$(obsidian-cli print-default 2>/dev/null | grep -i "path" | awk -F': ' '{print $2}' | xargs 2>/dev/null || true)
    fi

    if   [ -n "$OBSIDIAN_VAULT" ];                         then VAULT="$OBSIDIAN_VAULT"
    elif [ -n "$AUTO_VAULT" ] && [ -d "$AUTO_VAULT" ];     then VAULT="$AUTO_VAULT"
    elif [ -d "$HOME/Documents/OpenClaw-Vault" ];           then VAULT="$HOME/Documents/OpenClaw-Vault"
    else
        echo ""
        echo -e "  ${YELLOW}未检测到 Obsidian Vault，请输入路径:${NC}"
        echo -e "  ${DIM}（直接回车使用默认: ~/Documents/OpenClaw-Vault）${NC}"
        printf "  > "
        read -r VAULT_INPUT
        VAULT="${VAULT_INPUT:-$HOME/Documents/OpenClaw-Vault}"
    fi
    echo -e "  ${GREEN}✅${NC} Obsidian Vault: $VAULT"
else
    echo -e "  ${GREEN}✅${NC} Basic 模式 — 输出路径: ~/research/<project>/"
    echo -e "  ${DIM}   升级到 Full 后可迁移到 Obsidian Vault${NC}"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 3.  安装核心 Agents（两种模式都装）
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[3/8] 安装核心 Agents...${NC}"
mkdir -p "$WORKSPACE/agents"

for agent in paper-scout paper-analyzer review-lead; do
    TARGET="$WORKSPACE/agents/$agent"
    if [ -d "$TARGET" ]; then
        cp -r "$TARGET" "${TARGET}.bak.$(date +%s)" 2>/dev/null || true
        echo -e "  ${YELLOW}↺${NC}  agents/$agent（备份旧版 → 覆盖）"
    fi
    cp -r "$SCRIPT_DIR/agents/$agent" "$WORKSPACE/agents/"
    echo -e "  ${GREEN}✅${NC} agents/$agent"
done
echo ""

# ══════════════════════════════════════════════════════════════════
# 4.  安装 Skills
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[4/8] 安装 Skills...${NC}"
mkdir -p "$WORKSPACE/skills"

# ── 核心 Skills（Basic + Full 均装）
echo -e "  ${DIM}── 核心 Skills ──${NC}"
for skill in paper-scout paper-analyzer review-writer research-vault trendr-watchdog; do
    TARGET="$WORKSPACE/skills/$skill"
    if [ -d "$TARGET" ]; then
        cp -r "$TARGET" "${TARGET}.bak.$(date +%s)" 2>/dev/null || true
        echo -e "  ${YELLOW}↺${NC}  skills/$skill（备份旧版 → 覆盖）"
    fi
    cp -r "$SCRIPT_DIR/skills/$skill" "$WORKSPACE/skills/"
    echo -e "  ${GREEN}✅${NC} skills/$skill"
done

# ── 轻量依赖（两种模式均尝试）
echo ""
echo -e "  ${DIM}── 轻量依赖 Skills ──${NC}"
for skill in arxiv-watcher summarize agent-browser; do
    if [ -d "$WORKSPACE/skills/$skill" ]; then
        echo -e "  ${GREEN}✅${NC} $skill（已安装）"
    else
        echo -e "  ${CYAN}📦${NC} 安装 $skill..."
        npx clawhub@latest install "$skill" 2>/dev/null && \
            echo -e "  ${GREEN}✅${NC} $skill" || \
            echo -e "  ${YELLOW}⚠️${NC}  $skill 安装失败，手动: npx clawhub@latest install $skill"
    fi
done

# ── Full 专属 Skills
if [ "$INSTALL_MODE" = "full" ]; then
    echo ""
    echo -e "  ${DIM}── Full 模式专属 Skills ──${NC}"

    # nano-pdf
    if [ -d "$WORKSPACE/skills/nano-pdf" ]; then
        echo -e "  ${GREEN}✅${NC} nano-pdf（已安装）"
    else
        echo -e "  ${CYAN}📦${NC} 安装 nano-pdf..."
        npx clawhub@latest install nano-pdf 2>/dev/null && \
            echo -e "  ${GREEN}✅${NC} nano-pdf" || \
            echo -e "  ${YELLOW}⚠️${NC}  nano-pdf 安装失败，手动: npx clawhub@latest install nano-pdf"
    fi

    # context7
    if [ -d "$WORKSPACE/skills/context7" ] && [ -f "$WORKSPACE/skills/context7/ctx7" ]; then
        echo -e "  ${GREEN}✅${NC} context7（已安装）"
    else
        echo -e "  ${CYAN}📦${NC} 安装 context7 skill..."
        mkdir -p "$WORKSPACE/skills/context7"
        # SKILL.md
        cat > "$WORKSPACE/skills/context7/SKILL.md" << 'SKILL7EOF'
---
name: context7
description: Fetch up-to-date library/API documentation via Context7. No API key required. Use for coding, config, migration, CLI usage.
metadata: {"openclaw": {"emoji": "📖", "requires": {"bins": ["npx", "node"]}}}
---
# Context7 Skill
exec: node ~/.openclaw/workspace/skills/context7/ctx7 resolve "<library-name>"
exec: node ~/.openclaw/workspace/skills/context7/ctx7 docs "<library-id>" "<query>"
SKILL7EOF
        # ctx7 wrapper (minified for embed)
        cat > "$WORKSPACE/skills/context7/ctx7" << 'CTX7EOF'
#!/usr/bin/env node
'use strict';
const { spawn } = require('child_process');
const action = process.argv[2], arg1 = process.argv[3], arg2 = process.argv[4] || arg1;
if (!action || !arg1 || !['resolve','docs'].includes(action)) {
  console.error('Usage:\n  ctx7 resolve <library-name>\n  ctx7 docs <library-id> <query>');
  process.exit(1);
}
const toolName = action === 'resolve' ? 'resolve-library-id' : 'query-docs';
const toolArgs = action === 'resolve'
  ? { query: arg1, libraryName: arg1 }
  : { libraryId: arg1, query: arg2 };
const s = spawn('npx', ['-y', '@upstash/context7-mcp'], { stdio: ['pipe','pipe','inherit'] });
let buf = '', step = 'init';
s.stdout.on('data', c => {
  buf += c.toString();
  const ls = buf.split('\n'); buf = ls.pop();
  for (const r of ls) {
    const l = r.trim(); if (!l) continue;
    let m; try { m = JSON.parse(l); } catch { continue; }
    if (step === 'init' && m.id === 1 && m.result) {
      s.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized',params:{}})+'\n');
      s.stdin.write(JSON.stringify({jsonrpc:'2.0',id:2,method:'tools/call',params:{name:toolName,arguments:toolArgs}})+'\n');
      step = 'tool';
    } else if (step === 'tool' && m.id === 2) {
      if (m.error) { console.error(JSON.stringify(m.error)); cleanup(1); return; }
      for (const c of (m.result?.content ?? [])) { if (c.type === 'text') process.stdout.write(c.text+'\n'); }
      cleanup(0);
    }
  }
});
s.on('error', e => { console.error('ctx7:', e.message); process.exit(1); });
s.stdin.write(JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',
  params:{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'ctx7-cli',version:'2.0.0'}}})+'\n');
const t = setTimeout(() => { console.error('ctx7: timeout'); cleanup(1); }, 30000);
function cleanup(c) { clearTimeout(t); try { s.stdin.end(); s.kill('SIGTERM'); } catch {} process.exitCode = c; }
CTX7EOF
        chmod +x "$WORKSPACE/skills/context7/ctx7"
        echo -e "  ${GREEN}✅${NC} context7"
    fi

    # Scrapling
    echo ""
    echo -e "  ${DIM}── Scrapling 深挖层 ──${NC}"
    if command -v python3 >/dev/null 2>&1; then
        echo -e "  ${CYAN}📦${NC} pip3 install scrapling..."
        pip3 install scrapling --quiet 2>/dev/null && \
            SCRAPLING_OK=true && \
            echo -e "  ${GREEN}✅${NC} scrapling" || \
            echo -e "  ${YELLOW}⚠️${NC}  scrapling 安装失败，深挖模式降级为静态 API"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Python 3 未找到，scrapling 跳过"
    fi

    # obsidian-cli
    echo ""
    echo -e "  ${DIM}── Obsidian CLI ──${NC}"
    if command -v obsidian-cli >/dev/null 2>&1; then
        OBSIDIAN_OK=true
        echo -e "  ${GREEN}✅${NC} obsidian-cli（已安装）"
    elif command -v brew >/dev/null 2>&1; then
        echo -e "  ${CYAN}📦${NC} brew install obsidian-cli..."
        brew tap yakitrak/yakitrak 2>/dev/null && \
        brew install obsidian-cli 2>/dev/null && \
            OBSIDIAN_OK=true && \
            echo -e "  ${GREEN}✅${NC} obsidian-cli" || \
            echo -e "  ${YELLOW}⚠️${NC}  obsidian-cli 安装失败，手动: brew tap yakitrak/yakitrak && brew install obsidian-cli"
    else
        echo -e "  ${YELLOW}⚠️${NC}  brew 未找到，obsidian-cli 跳过（手动安装后重跑即可）"
    fi

    # Playwright 回退层（询问）
    echo ""
    echo -e "  ${DIM}── Playwright 回退层（可选安装）──${NC}"
    echo -e "  ${YELLOW}注意:${NC} Playwright 不进默认检索链，仅在 JS 渲染/登录态时触发"
    printf "  是否现在安装 Playwright？[y/N]: "
    read -r PW_INPUT
    if [[ "$PW_INPUT" =~ ^[Yy]$ ]]; then
        echo -e "  ${CYAN}📦${NC} npm install -g @playwright/mcp..."
        npm install -g @playwright/mcp 2>/dev/null && \
            PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright" npx -g playwright install chromium 2>/dev/null && \
            echo -e "  ${GREEN}✅${NC} playwright-mcp + Chromium" || \
            echo -e "  ${YELLOW}⚠️${NC}  Playwright 安装失败，跳过"
    else
        echo -e "  ${DIM}  跳过（稍后: npm install -g @playwright/mcp）${NC}"
    fi
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 5.  注册 Skills 到 openclaw.json
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[5/8] 注册 Skills 到 openclaw.json...${NC}"
OC_JSON="$HOME/.openclaw/openclaw.json"

_ensure_skill() {
    local sk="$1"
    python3 - "$OC_JSON" "$sk" << 'PYEOF'
import json, sys
path, skill = sys.argv[1], sys.argv[2]
with open(path) as f: c = json.load(f)
entries = c.setdefault('skills', {}).setdefault('entries', {})
if skill not in entries:
    entries[skill] = {'enabled': True}
    with open(path, 'w') as f: json.dump(c, f, indent=2, ensure_ascii=False)
    print(f'  added: {skill}')
else:
    print(f'  already registered: {skill}')
PYEOF
}

_ensure_agent_tool() {
    local agent_id="$1"
    local tool_name="$2"
    python3 - "$OC_JSON" "$agent_id" "$tool_name" << 'PYEOF'
import json, sys
path, agent_id, tool_name = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    c = json.load(f)
agents = c.setdefault('agents', {}).setdefault('list', [])
target = next((a for a in agents if a.get('id') == agent_id), None)
if not target:
    print(f'  agent not found: {agent_id}')
    raise SystemExit(0)
allow = target.setdefault('tools', {}).setdefault('allow', [])
if tool_name not in allow:
    allow.append(tool_name)
    with open(path, 'w') as f:
        json.dump(c, f, indent=2, ensure_ascii=False)
    print(f'  added tool for {agent_id}: {tool_name}')
else:
    print(f'  tool already allowed for {agent_id}: {tool_name}')
PYEOF
}

BASE_SKILLS="paper-scout paper-analyzer review-writer research-vault trendr-watchdog arxiv-watcher summarize agent-browser"
for sk in $BASE_SKILLS; do _ensure_skill "$sk"; done
_ensure_agent_tool "review-lead" "sessions_yield"

if [ "$INSTALL_MODE" = "full" ]; then
    for sk in nano-pdf context7 zotero; do _ensure_skill "$sk"; done
fi

# Validate JSON
node -e "JSON.parse(require('fs').readFileSync('$OC_JSON','utf8'))" && \
    echo -e "  ${GREEN}✅${NC} openclaw.json 语法合法" || \
    echo -e "  ${RED}❌${NC} openclaw.json 语法错误！请检查"
echo ""

# ══════════════════════════════════════════════════════════════════
# 6.  初始化输出目录
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[6/8] 初始化输出目录...${NC}"
mkdir -p "$HOME/research"
echo -e "  ${GREEN}✅${NC} 研究工作目录: ~/research/"

if [ "$INSTALL_MODE" = "full" ] && [ -n "$VAULT" ]; then
    mkdir -p "$VAULT/Research/"{_index,papers,reviews,daily,templates}

    POOL="$VAULT/Research/_index/paper-pool.csv"
    if [ ! -f "$POOL" ]; then
        echo "paper_id,title,authors,year,venue,source,citation_count,doi,project,added_date,tags,status" > "$POOL"
        echo -e "  ${GREEN}✅${NC} 论文池索引创建: Research/_index/paper-pool.csv"
    else
        TOTAL=$(tail -n +2 "$POOL" | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✅${NC} 论文池已存在（$TOTAL 篇）"
    fi

    # 论文卡片模板
    cat > "$VAULT/Research/templates/paper-card.md" << 'TEOF'
---
paper_id: "{{paper_id}}"
title: "{{title}}"
authors: {{authors}}
year: {{year}}
venue: "{{venue}}"
project: "{{project}}"
tags: {{tags}}
status: analyzed
---
# {{title}}
> **项目**: [[reviews/{{project}}/review|{{project}}]]
## 研究问题
## 方法
## 关键结果
## 主要贡献
## 局限性
## BibTeX
TEOF
    echo -e "  ${GREEN}✅${NC} Obsidian 模板已创建"

    # obsidian-cli 写入测试
    if command -v obsidian-cli >/dev/null 2>&1; then
        VAULT_NAME=$(basename "$VAULT")
        obsidian-cli create "_trendr-test" --vault "$VAULT_NAME" \
            --content "# TrendR Install v${VERSION} $(date)" 2>/dev/null && \
            rm -f "$VAULT/_trendr-test.md" 2>/dev/null && \
            echo -e "  ${GREEN}✅${NC} obsidian-cli 写入测试通过" || \
            echo -e "  ${YELLOW}⚠️${NC}  obsidian-cli 写入测试失败，请确认:"
        echo -e "     ${DIM}obsidian-cli set-default --vault $VAULT_NAME${NC}"
    fi
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# 7.  安装 TrendR 协议文件
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[7/8] 安装 TrendR 协议文件...${NC}"
mkdir -p "$WORKSPACE/protocols"

for p in trendr-protocol.md research-team-protocol.md; do
    if [ -f "$SCRIPT_DIR/protocols/$p" ]; then
        cp "$SCRIPT_DIR/protocols/$p" "$WORKSPACE/protocols/$p"
        echo -e "  ${GREEN}✅${NC} protocols/$p"
    else
        echo -e "  ${YELLOW}⚠️${NC}  缺少模板: $SCRIPT_DIR/protocols/$p（跳过）"
    fi
done
echo ""

# ══════════════════════════════════════════════════════════════════
# 8.  更新 AGENTS.md
# ══════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}[8/8] 更新 AGENTS.md...${NC}"
AGENTS_MD="$WORKSPACE/AGENTS.md"
touch "$AGENTS_MD"

# 兼容旧版：若已存在 TrendR 段落，先删除旧段再写入新版
if grep -q "## 📚 TrendR — 自动化文献综述工作流" "$AGENTS_MD" 2>/dev/null; then
    awk '
    BEGIN { keep=1 }
    /## 📚 TrendR — 自动化文献综述工作流/ { keep=0 }
    keep { print }
    ' "$AGENTS_MD" > "$AGENTS_MD.tmp" && mv "$AGENTS_MD.tmp" "$AGENTS_MD"
    echo -e "  ${YELLOW}↺${NC}  已移除旧版 TrendR 段落"
fi

VAULT_DISPLAY="${VAULT:-~/research/<project>}"
cat >> "$AGENTS_MD" << AGEOF

---

## 📚 TrendR — 自动化文献综述工作流 (v${VERSION}, ${INSTALL_MODE} mode)

### 触发词
"帮我调研..."、"文献综述"、"survey"、"最新进展"、"research review"、"搜索论文"

### 主链架构
\`\`\`
9-source APIs (paper-scout)
  → [Full: Scrapling 深挖] → [Full: Zotero 导入]
  → paper-analyzer → review-writer
  → [Full: research-vault → Obsidian]
回退层: Playwright（仅满足 5 种条件时触发，见 Search Escalation Rule）
\`\`\`

### /trendr 交互模式（参数化入口）
当用户输入 \`/trendr\`、\`/trendr 主题...\`、\`trendr 研究 ...\`（或任意包含 \`trendr\` 的研究请求）时，统一先收集参数，再执行：
- 研究主题（必填，一句话）
- 研究源头规模：\`A=20-30\` / \`B=30-50\` / \`C=50-100\`
- 研究轮次：\`A=1-3\` / \`B=3-6\` / \`C=6-10\`
- 研究程度：\`A=轻度\` / \`B=中度\` / \`C=深度\`
- 用户可接受时长（分钟）
- 用户可以只输入字母（A/B/C）而不必重复打字
- 若缺少研究主题，不得进入 ETA 计算，必须先追问主题
- 若仅给主题（如：\`/trendr 主题：智能体决策系统\` 或 \`trendr 研究 智能体决策系统\`），参数仍不完整，必须继续询问，不得开跑
- 在用户确认 \`y/yes/确认/开始/继续\` 前，禁止派发任何 subagent（含 \`review-lead\`）
- 在确认前，禁止输出“已启动/已派发/流水线执行中”等执行态文案

TrendR 首条回复必须使用如下模板（不得省略研究主题）：
\`\`\`
/trendr 启动！这是参数化研究流程，当前是快速模式，请先选择：
（若要进入精确模式调整，输入：/b)

1) 研究主题（必填）
2) 研究轮次：A/B/C
   - A = 1-3 轮（轻量）
   - B = 3-6 轮（标准）
   - C = 6-10 轮（深度）

3) 研究程度：A/B/C
   - A = API 标准检索（快）
   - B = API + Scrapling（更全）
   - C = API + Scrapling + Tavily（常规最强）

4) 时间预算（分钟）

示例：主题：RL 多智能体做市；B / B / 60
\`\`\`

先给出计划预估，不要直接开跑：
- 估时模型：\`eta = 8 + source_factor + round_factor + depth_factor\`
- \`source_factor\`: A=10, B=22, C=40
- \`round_factor\`: A=8, B=20, C=35
- \`depth_factor\`: A=0, B=10, C=20
- 若用户预算 < \`eta * 0.7\`：自动调整计划（先降轮次，再降源头规模），并解释原因

执行前必须回显：
1. 调整后计划（源头/轮次/深度）
2. 预计耗时与预计完成时间（本地时区）
3. 询问“是否确认执行？（y / n）”

### 运行可视化与日志（必做）
\`\`\`
session_status: {}
### 记录当前主会话 ID 到 [OWNER_SESSION_ID]
exec: mkdir -p ~/research/[PROJECT]/{papers,notes,logs}
exec: RUN_ID=$(date +%Y%m%d_%H%M%S); echo "$RUN_ID" > ~/research/[PROJECT]/logs/.current_run_id
write: ~/research/[PROJECT]/run_status.json
{
  "run_id":"[RUN_ID]",
  "status":"running",
  "phase":"init",
  "progress_percent":0,
  "owner_session_id":"[OWNER_SESSION_ID]",
  "started_at":"[ISO8601]",
  "eta_minutes":[ETA_MIN]
}
write: ~/research/[PROJECT]/progress.md
[----------] 0% | Phase 0/5 | 初始化
exec: PROJECT="[PROJECT]" && RUN_ID="[RUN_ID]" && SESSION_ID="[OWNER_SESSION_ID]" && nohup python3 ~/.openclaw/workspace/skills/trendr-watchdog/supervisor.py --project "\$PROJECT" --run-id "\$RUN_ID" --session-id "\$SESSION_ID" --poll-sec 60 --idle-timeout-sec 600 --phase-mismatch-grace-sec 180 --artifact-complete-grace-sec 1800 --resume-cooldown-sec 300 --heartbeat-sec 300 --max-resume 12 >> ~/research/"\$PROJECT"/logs/watchdog.out 2>&1 & echo \$! > ~/research/"\$PROJECT"/logs/watchdog.pid
\`\`\`

刷新规则（强制）：
- 每个 phase 开始/结束都要刷新 \`run_status.json + progress.md\`
- 每 5-10 分钟至少写一次心跳（即使无新结果）
- 事件日志追加到 \`~/research/[PROJECT]/logs/[RUN_ID].log\`
- 每次写完日志后同步覆盖 \`~/research/[PROJECT]/logs/latest.log\`
- watchdog 会在“10 分钟无更新”或“文件已到下一阶段但 phase 未推进 3 分钟”时自动注入续接指令

### Phase 1 — 论文搜索（必须先读 SKILL.md）
\`\`\`
write: ~/research/[PROJECT]/progress.md
[##--------] 20% | Phase 1/5 Discovery | 召回候选论文
sessions_spawn: {
  task: "先读 skills/paper-scout/SKILL.md，搜索：\n[queries]\n项目: ~/research/[PROJECT]/。若 web_fetch 出现 private/internal/special-use IP 拦截，切到 arxiv-watcher + tavily-search + web_search + browser 兜底，并仍输出 candidates.csv。",
  agentId: "paper-scout", mode: "run", runTimeoutSeconds: 900
}
# 必须阻塞等待到终态，不能只回“已启动”
sessions_yield: { sessionId: "[SCOUT_SESSION_ID]" }
read: ~/research/[PROJECT]/candidates.csv
read: ~/research/[PROJECT]/search_log.md
\`\`\`
输出: candidates.csv + search_log.md
若用户设置了候选数量下限（A/B/C 对应 20-30/30-50/50-100），未达标则继续补检索直到达标或写明失败原因。

### Phase 2 — 精读（relevance_score >= 4）
\`\`\`
write: ~/research/[PROJECT]/progress.md
[#####-----] 55% | Phase 2/5 Analysis | 精读与结构化提取
sessions_spawn: {
  task: "先读 skills/paper-analyzer/SKILL.md，分析：\n[paper_ids]\n项目: ~/research/[PROJECT]/",
  agentId: "paper-analyzer", mode: "run", runTimeoutSeconds: 1200
}
sessions_yield: { sessionId: "[ANALYZER_SESSION_ID]" }
read: ~/research/[PROJECT]/matrix.csv
\`\`\`
输出: notes/*.md + matrix.csv

### Phase 3 — 空白检测
write: ~/research/[PROJECT]/progress.md
[#######---] 80% | Phase 3/5 Gap Check | 覆盖率检查
读 notes + matrix.csv → 有空白 → 回 Phase 1 → 充分 → Phase 4

### Phase 4 — 撰写综述
write: ~/research/[PROJECT]/progress.md
[#########-] 95% | Phase 4/5 Writing | 生成综述
先读 \`skills/review-writer/SKILL.md\` → 输出 review.md + references.bib

### Phase 5 — 持久化（Full 模式）
write: ~/research/[PROJECT]/progress.md
[##########] 100% | Phase 5/5 Persist | 完成
先读 \`skills/research-vault/SKILL.md\` → candidates.csv → Obsidian 论文池 → 论文卡片 → reviews/ → daily/
exec: PROJECT="[PROJECT]" && PID_FILE=~/research/"\$PROJECT"/logs/watchdog.pid && if [ -f "\$PID_FILE" ]; then kill "\$(cat \"\$PID_FILE\")" 2>/dev/null || true; fi

### ⚠️ 防遗忘规则
派发 subagent 时，任务描述必须以 "先读 skills/xxx/SKILL.md" 开头。
禁止在 subagent 仍在运行时宣布完成。必须看到本阶段输出文件后再进入下一阶段。

AGEOF
echo -e "  ${GREEN}✅${NC} AGENTS.md 已更新 TrendR 工作流"
echo ""

# ══════════════════════════════════════════════════════════════════
# 完成
# ══════════════════════════════════════════════════════════════════
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║              TrendR v${VERSION} 安装完成！                       ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}模式:${NC} $([ "$INSTALL_MODE" = "full" ] && echo "${CYAN}Full${NC}" || echo "${GREEN}Basic${NC}")"
echo -e "  ${BOLD}Agents:${NC}  paper-scout · paper-analyzer · review-lead"
echo -e "  ${BOLD}Skills:${NC}  paper-scout (9源) · paper-analyzer · review-writer · research-vault · trendr-watchdog"
if [ "$INSTALL_MODE" = "full" ]; then
    EXTRAS="nano-pdf · context7"
    [ "$SCRAPLING_OK" = "true" ] && EXTRAS="$EXTRAS · scrapling"
    [ "$OBSIDIAN_OK"  = "true" ] && EXTRAS="$EXTRAS · obsidian-cli"
    echo -e "  ${BOLD}Full 层:${NC} $EXTRAS"
    [ -n "$VAULT" ] && echo -e "  ${BOLD}Vault:${NC}   $VAULT/Research/"
fi
echo ""

# ── 后续操作清单（只列真正需要的）
echo -e "${BOLD}  后续操作清单:${NC}"
STEP=1

if [ "$INSTALL_MODE" = "full" ] && [ "$OBSIDIAN_OK" != "true" ]; then
    echo "  $STEP. 安装 obsidian-cli（Obsidian 持久化依赖）:"
    echo "     brew tap yakitrak/yakitrak && brew install obsidian-cli"
    STEP=$((STEP+1))
fi

if [ "$INSTALL_MODE" = "full" ] && [ "$ZOTERO_OK" != "true" ]; then
    echo "  $STEP. 配置 Zotero（在 openclaw.json → skills.entries.zotero.env 填入）:"
    echo "     ZOTERO_API_KEY=<key>  ZOTERO_USER_ID=<id>"
    echo "     获取: https://www.zotero.org/settings/keys"
    STEP=$((STEP+1))
fi

if [ "$DNS_FAKE_IP" = "true" ]; then
    echo "  $STEP. 检测到 DNS Fake-IP（198.18.x.x），建议关闭代理 fake-ip 或改 redir-host："
    echo "     受影响域名: $DNS_FAKE_IP_HITS"
    echo "     说明: TrendR 已启用兜底检索，但主链 API 命中率会受影响"
    STEP=$((STEP+1))
fi

if [ "$INSTALL_MODE" = "full" ] && command -v obsidian-cli >/dev/null 2>&1; then
    echo "  $STEP. 设置 obsidian-cli 默认 vault:"
    echo "     obsidian-cli set-default --vault $(basename "${VAULT:-OpenClaw-Vault}")"
    STEP=$((STEP+1))
fi

echo "  $STEP. 重启 OpenClaw gateway:"
echo "     openclaw gateway restart"
STEP=$((STEP+1))

echo "  $STEP. 对 Mac_Javis 说:"
echo "     '帮我调研 [主题] 的最新进展'"
echo "     '快速扫描 [主题]'  ← 只搜索，不精读"
echo "     '/trendr'          ← 交互式选择规模/轮次/深度/时长"
if [ "$INSTALL_MODE" = "full" ] && [ "$SCRAPLING_OK" = "true" ]; then
    echo "     '深挖 [主题]'       ← 开启 Scrapling 深挖"
fi
echo "  $STEP. 运行中查看进度/日志:"
echo "     cat ~/research/<project>/progress.md"
echo "     tail -f ~/research/<project>/logs/latest.log"
STEP=$((STEP+1))
echo ""

if [ "$INSTALL_MODE" = "basic" ]; then
    echo -e "  ${DIM}升级到 Full: 重新运行 install.sh → 选 [2]${NC}"
fi
echo -e "  ${DIM}卸载: bash $(dirname "$0")/uninstall.sh${NC}"
echo ""
