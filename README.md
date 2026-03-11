<p align="center">
  <h1 align="center">TrendR</h1>
  <p align="center"><strong>趋势研究 — 自动化文献综述 + Obsidian 知识管理</strong></p>
  <p align="center">3 个 Agent · 4 个 Skill · 9 源搜索 · 零额外 MCP 依赖</p>
  <p align="center">
    <a href="#安装">安装</a> · <a href="#使用方法">使用</a> · <a href="#系统架构">架构</a> · <a href="#横向对比">对比</a>
  </p>
  <p align="center">
    <a href="./README_EN.md">English</a> | 中文
  </p>
</p>

---

告诉你的 Agent 一句话，剩下的它来做。

```
你: "调研多智能体系统在金融领域的最新进展"

TrendR:
  → 9 源并行搜索，找到 47 篇候选论文
  → 精读 12 篇论文，结构化笔记 + 对比矩阵
  → 21KB 文献综述（分类体系、差距分析、BibTeX）
  → 自动归档到 Obsidian，论文池持久化
  → 通知你：完成 ✅
```

灵感来源于 [karpathy/autoresearch](https://github.com/karpathy/autoresearch) 的自主研究循环，从「LLM 训练优化」重新设计为「论文搜索 + 文献综述」。

---


<img width="2752" height="1536" alt="Gemini_Generated_Image_72p26b72p26b72p2" src="https://github.com/user-attachments/assets/4cd94b4a-6ca1-4515-8a0c-835d551994d2" />


## 它解决什么问题

| 步骤 | 手动 | TrendR |
|------|------|--------|
| 跨平台论文搜索 | 3-4 小时 | 5 分钟（9 源并行） |
| 筛选相关论文 | 2-3 小时 | 自动评分 1-5 + 去重 |
| 精读 + 做笔记 | 8-12 小时 | 结构化提取（问题/方法/结果/局限） |
| 撰写综述报告 | 6-8 小时 | 自动生成（分类体系 + 分析 + 研究空白） |
| 整理参考文献 | 1-2 小时 | 自动 BibTeX |
| 归档到知识库 | 1 小时 | 自动同步到 Obsidian |
| **合计** | **约 20-30 小时** | **约 30 分钟等待** |

---

## 包含内容

| 类型 | 名称 | 职责 |
|------|------|------|
| Agent | `paper-scout` | 9 源搜索 + 评分 + 去重 |
| Agent | `paper-analyzer` | 精读 + 结构化笔记 + 对比矩阵 |
| Agent | `review-lead` | 编排流水线 + 撰写综述 + Obsidian 持久化 |
| Skill | `paper-scout` | 9 个学术 API 调用手册（10KB） |
| Skill | `paper-analyzer` | 结构化提取模板 |
| Skill | `review-writer` | 综述写作模板 + 质量清单 |
| Skill | `research-vault` | Obsidian 持久化 + 论文池索引 |

---

## 前置要求

- macOS 或 Linux
- Node.js 22+
- 已安装 [OpenClaw](https://openclaw.ai) 并完成 `openclaw onboard`
- 已安装 [Obsidian](https://obsidian.md)
- OpenClaw 支持的任意 LLM（MiniMax M2.5 / Claude / GPT 等）

---

## 安装

```bash
git clone https://github.com/yourname/trendr.git
cd trendr
chmod +x install.sh
./install.sh
```

自定义 Obsidian 仓库路径：

```bash
OBSIDIAN_VAULT="/your/vault/path" ./install.sh
```

### 安装器做了什么（8 步）

| 步骤 | 动作 |
|------|------|
| 0 | 检测环境：Node.js、npx、OpenClaw、workspace、Obsidian vault |
| 1 | 通过 ClawHub 安装 7 个依赖 Skill（arxiv-watcher、tavily-search、summarize、deep-research、playwright-mcp、agent-browser、obsidian） |
| 2 | 安装 Playwright 浏览器（chromium） |
| 3 | 复制 3 个 Agent → `workspace/agents/` |
| 4 | 复制 4 个 Skill → `workspace/skills/` |
| 5 | 检测 Obsidian vault 路径，注入到 Skill 配置中 |
| 6 | 初始化 Obsidian `Research/` 目录 + 论文池 + 模板，同步已有数据 |
| 7 | 将 TrendR 工作流追加到 AGENTS.md（含强制 Obsidian 自动保存） |
| 8 | 提示用户验证 `openclaw.json` 配置 |

### 本地obsidian 开启cli 

1.打开obsidian, 设置》〉通用〉》Command line interface〉》开启
2. Terminal输入
```shell
obsidian-cli set-default --vault OpenClaw-Vault
obsidian-cli print-default
```
应该显示 OpenClaw-Vault 和路径 /Users/mac/Documents/OpenClaw-Vault。
测试写入：
```shell
obsidian-cli create "test-note" --vault OpenClaw-Vault --content "# Hello from CLI"
```

### 检查openclaw UI skills 是eligible
通过本地 UI界面检查所有skills状态，哪个有问题，让AI 一个一个调试：
<img width="902" height="829" alt="Screenshot 2026-03-11 at 12 14 17" src="https://github.com/user-attachments/assets/4ff121ee-5b36-4ef6-89e1-5a1271026d17" />


### 安装后：验证 openclaw.json

确保 `~/.openclaw/openclaw.json` 包含以下内容：

**1. agents.list** — 注册三个子 Agent：

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "default": true,
        "subagents": {
          "allowAgents": ["paper-scout", "paper-analyzer", "review-lead"]
        }
      },
      { "id": "paper-scout",    "name": "Paper Scout",    "workspace": "~/.openclaw/workspace" },
      { "id": "paper-analyzer", "name": "Paper Analyzer", "workspace": "~/.openclaw/workspace" },
      { "id": "review-lead",    "name": "Review Lead",    "workspace": "~/.openclaw/workspace" }
    ]
  }
}
```

**2. skills.entries** — 启用所有相关 Skill：

```json
"paper-scout": { "enabled": true },
"paper-analyzer": { "enabled": true },
"review-writer": { "enabled": true },
"research-vault": { "enabled": true }
```

**3. maxTokens** >= 32768（否则 analyzer 输出会被截断）

然后：

```bash
openclaw gateway restart
```

---

## 使用方法

```bash
# 新建文献综述
"调研 [主题] 的最新进展"

# 搜索论文
"搜索关于自主 AI Agent 的论文，聚焦 2024-2025，偏好有代码的"

# 查询论文池
"在我的论文池中查找关于 transformer 的论文"
"按项目统计论文池"

# 继续一个项目
"继续 rl-multi-agent-finance 项目，新增做市方向"

# 同步到 Obsidian
"将研究成果同步到 Obsidian"

# 每日追踪
"设置每天早上 9 点的 arXiv cs.AI 追踪"
```

---

## 系统架构

### 整体概览

```
┌──────────────────────────────────────────────────────────┐
│                         用户                              │
│                Telegram / 飞书 / Web                      │
└─────────────────────┬────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────────────┐
│           OpenClaw Gateway（本地运行）                      │
│                                                          │
│  ┌─ main agent ───────────────────────────────────────┐  │
│  │  接收 → 分解 → 分派 → 综合                           │  │
│  └──────┬──────────────┬──────────────┬───────────────┘  │
│         ▼              ▼              ▼                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │  paper-   │  │  paper-   │  │  review-  │           │
│  │  scout    │  │  analyzer │  │  lead     │           │
│  │  搜索     │  │  精读     │  │  撰写     │           │
│  │  评分     │  │  提取     │  │  归档     │           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │              │              │                   │
│  ┌─────▼──────────────▼──────────────▼───────────────┐  │
│  │  Skills（Markdown 格式的工具指令）                    │  │
│  ├────────────────────────────────────────────────────┤  │
│  │  Tools（exec / web_fetch / read / write / browser） │  │
│  └────────────────────────────────────────────────────┘  │
└─────────┬───────────────────────────────┬────────────────┘
          ▼                               ▼
 ┌─────────────────┐          ┌──────────────────────┐
 │  9 个学术 API    │          │  Obsidian Vault       │
 │  （全部免费）     │          │  论文池 + 卡片 + 综述  │
 └─────────────────┘          └──────────────────────┘
```

### 流水线

```
阶段 1: 搜索 ──→ candidates.csv（40-100 篇论文）
                  search_log.md
         │
阶段 2: 分析 ──→ notes/*.md（10-30 篇结构化笔记）
                  matrix.csv（对比矩阵）
         │
阶段 3: 缺口检查 → 不够？→ 回到阶段 1
                   够了？→ 阶段 4
         │
阶段 4: 撰写 ──→ review.md（15-25KB 文献综述）
                  references.bib
         │
阶段 5: 持久化 → Obsidian paper-pool.csv（累积去重）
                  Obsidian papers/*.md（带 wiki-links 的卡片）
                  Obsidian reviews/project/（归档）
                  Obsidian daily/date.md（研究日志）
         │
阶段 6: 报告 ──→ 通过 Telegram/飞书 通知用户
```

### 9 源搜索覆盖

所有 API 均为公开免费，通过 `web_fetch` 直接调用——无需额外 MCP 服务：

| # | 来源 | 覆盖范围 | 需要密钥 |
|---|------|----------|---------|
| 1 | arXiv | 计算机/数学/物理预印本 | 否 |
| 2 | Semantic Scholar | 2 亿+ 论文，引用图谱 | 推荐（免费） |
| 3 | OpenAlex | 2.5 亿+ 作品，完全开放 | 否 |
| 4 | PubMed | 3600 万+ 生物医学 | 否 |
| 5 | CrossRef | 1.4 亿+ DOI 注册 | 否 |
| 6 | DBLP | 计算机科学文献 | 否 |
| 7 | Europe PMC | 4000 万+ 生命科学 | 否 |
| 8 | bioRxiv | 生物学预印本 | 否 |
| 9 | Papers with Code | ML 论文 + 代码仓库 | 否 |

Agent 根据研究领域自动选择 3-5 个最相关的来源。

### Obsidian 知识库

```
[Vault]/Research/
├── _index/
│   └── paper-pool.csv          ← 论文池（跨项目累积）
├── papers/
│   └── 2301.12345.md           ← 论文卡片（YAML frontmatter + wiki-links）
├── reviews/
│   └── project-name/
│       ├── review.md
│       ├── references.bib
│       └── matrix.csv
├── daily/
│   └── 2026-03-10.md           ← 每日研究日志
└── templates/
```

论文池 CSV 追踪状态流转：`candidate` → `analyzed` → `cited_in_review`

### 防遗忘机制

使用非前沿模型（如 MiniMax M2.5）时，Agent 可能忘记读取 Skill 文件。TrendR 采用三层防御：

| 层级 | 机制 |
|------|------|
| AGENTS.md | 硬编码规则："任务描述必须包含 '先读 skills/xxx/SKILL.md'" |
| SOUL.md | 顶部警告："⚠️ 第一步：读 skills/xxx/SKILL.md" |
| SKILL.md | 完整的可复制粘贴命令，而非抽象指令 |

---

## 横向对比

### TrendR vs autoresearch vs paper-distill-mcp

```
              论文发现      精读分析      文献综述      知识管理
             ──────────   ──────────   ──────────   ──────────
autoresearch      ·            ·            ·            ·

distill-mcp   ████████        █            ·         ████

TrendR        ████████     ████████     ████████     ████████
              9 源搜索     结构化笔记    完整综述     Obsidian + 论文池
```

### 功能矩阵

| 维度 | autoresearch | paper-distill-mcp | TrendR |
|------|-------------|-------------------|--------|
| **定位** | LLM 训练优化 | 论文发现 + 推送 | **完整文献综述流水线** |
| **核心循环** | 改代码 → 训练 5min → 评估 | 搜索 9 源 → 评分 → 推送 | **搜索 → 精读 → 写综述 → 归档** |
| **硬件** | NVIDIA H100 | 任意（API 调用） | **Mac / Linux（API 调用）** |
| **单次成本** | GPU 电费 | 约 ¥20-60（Claude/GPT） | **约 ¥0-7（MiniMax）** |
| **搜索源** | N/A | 9 个 | **9 个** |
| **评分** | val_bpb（硬指标） | 4 维加权（代码） | 1-5 分（Agent） |
| **论文池** | N/A | ✅ 持久化 | **✅ Obsidian CSV** |
| **精读** | N/A | ❌ 单行摘要 | **✅ 结构化笔记** |
| **对比矩阵** | N/A | ❌ | **✅ matrix.csv** |
| **文献综述** | N/A | ❌ | **✅ 完整综述** |
| **Obsidian** | N/A | ✅ 笔记卡片 | **✅ 卡片 + 综述 + 日志 + 论文池** |
| **Zotero** | N/A | ✅ | ❌（可扩展） |
| **双 AI 审稿** | ❌ | ✅ | ❌（可扩展） |
| **Agent 架构** | 单 Agent | 无 Agent（纯工具） | **多 Agent（3 个子 Agent）** |
| **额外依赖** | PyTorch + GPU | Python 包 | **无（仅 web_fetch）** |
| **许可证** | MIT | AGPL-3.0 | **MIT** |

### 设计哲学

**autoresearch** — *"把实验循环交给 AI"*。人写 `program.md`（策略），AI 写 `train.py`（代码）。优雅的约束设计：单文件、固定 5 分钟预算、单一指标。但需要 GPU。

**paper-distill-mcp** — *"把筛选苦力活交给代码"*。搜索/评分/去重是确定性操作——Python 代码比 LLM 便宜 100 倍。19 个工具函数、4 维评分、论文池状态机。工程扎实。但止步于"推送 6 篇论文 + 单行摘要"。

**TrendR** — *"把整个文献综述交给多 Agent 协作"*。论文搜索很便宜（免费 API）。**精读和综述撰写才是真正的价值**。3 个专业子 Agent、Skill 文件作为可执行知识、Obsidian 做持久化知识管理。零额外依赖——Agent 直接调用公开 API。

### 互补使用

三个项目并非互斥。最强组合：

```
paper-distill-mcp（替换 paper-scout 作为搜索前端）
  → 4 维加权评分 + 代码级去重 + 双 AI 审稿

TrendR analyzer + writer + vault（保留作为后端）
  → 结构化笔记 + 综述撰写 + Obsidian 持久化
```

TrendR 已天然兼容——阶段 1 可被任何能产出 `candidates.csv` 的方案替换。

---

## 成本分析

使用 MiniMax M2.5（$0.30/1M 输入，$1.20/1M 输出）：

| 阶段 | Token 数 | 成本 |
|------|----------|------|
| 阶段 1: 搜索 | 约 100K | 约 $0.15 |
| 阶段 2: 精读 20 篇 | 约 400K | 约 $0.60 |
| 阶段 3: 缺口检查 | 约 50K | 约 $0.08 |
| 阶段 4: 撰写综述 | 约 200K | 约 $0.30 |
| 阶段 5: 持久化 | 约 30K | 约 $0.05 |
| **合计** | **约 780K** | **约 $1.18** |

使用 MiniMax Portal（免费 OAuth 额度）：**$0**。

| 方案 | 单次 | 月度（4 次） |
|------|------|-------------|
| TrendR + MiniMax 免费 | $0 | $0 |
| TrendR + MiniMax API | 约 $1.2 | 约 $5 |
| paper-distill + Claude | 约 $3-5 | 约 $15-20 |
| 人工（按 $30/hr） | 约 $240 | 约 $960 |

---

## 自定义

**添加搜索源**：编辑 `skills/paper-scout/SKILL.md`，按现有格式添加新的 `web_fetch` 调用。

**修改综述模板**：编辑 `skills/review-writer/SKILL.md`。

**修改笔记字段**：编辑 `skills/paper-analyzer/SKILL.md`。

**切换模型**：TrendR 与模型无关。在 `openclaw.json` 中配置——MiniMax、Claude、GPT、DeepSeek 均可。

**每日论文追踪**：告诉你的 Agent："设置每天早上 9 点的 arXiv cs.AI 追踪"。

---

## 已知局限

- **非实时**：学术 API 有速率限制（arXiv: 3 秒/请求）；完整搜索需要几分钟
- **非前沿模型可能遗忘**：MiniMax M2.5 有时会跳过 Skill 文件，尽管有三层防御
- **全文阅读受限**：大多数论文通过摘要页分析；完整 PDF 解析取决于下载 + 解析能力
- **无 Zotero 集成**：可扩展（参考 paper-distill-mcp 的实现）
- **无双 AI 审稿**：可扩展（参考 paper-distill-mcp 的双审模式）

---

## 卸载

```bash
chmod +x uninstall.sh
./uninstall.sh
```

你的 Obsidian 研究数据和 `~/research/` 会被保留。

---

## 致谢

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 自主研究循环的灵感来源
- [paper-distill-mcp](https://github.com/Eclipse-Cj/paper-distill-mcp) — 多源搜索架构参考
- [OpenClaw](https://openclaw.ai) — Agent 运行时基础设施

## 许可证

MIT
