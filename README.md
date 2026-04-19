<p align="center">
  <h1 align="center">TrendR</h1>
  <p align="center"><strong>A research-agent harness for recoverable literature review</strong></p>
  <p align="center">Turn paper discovery, analysis, writing, and verification into a resumable, traceable control plane.</p>
  <p align="center">
    <a href="#what-trendr-is">What TrendR is</a> ·
    <a href="#core-capabilities">Core capabilities</a> ·
    <a href="#workflow-vs-harness">Workflow vs Harness</a> ·
    <a href="#reliability-and-engineering-proof">Reliability proof</a> ·
    <a href="#optional-extensions">Optional extensions</a> ·
    <a href="#quick-start">Quick start</a>
  </p>
  <p align="center">
    <a href="./README_EN.md">English</a> | 中文
  </p>
</p>

## 能力上限速览

给定一个研究命题，当前链路的实测上限：

| 指标 | 实际可达上限 | 理论绝对上限 | 限制来源 |
|------|------------|------------|---------|
| Discovery 轮数 | **6 轮** | 12 轮（×resume） | 状态机硬编码 |
| 单次运行时长 | **~5 小时** | 60 小时（12 次 resume） | state timeout 累积 |
| 页面访问量 | **600–1000 次** | ~2000 次 | 轮数 × 源数 |
| 候选论文池 | **650 篇** | ~1000 篇 | 去重后收敛 |
| 实际分析论文 | **80 篇**（Depth C） | 80 篇（target_papers 卡口） | CLI 配置值 |
| Obsidian 节点 | **80 张/run**，累积无上限 | 累积数千（多次运行） | 磁盘空间 |
| Zotero 同步 | **手动导入 .bib** | 自动同步（需实现） | Stub |

**当前链路三个关键断点：**

- **分析能力 ≪ 收集能力**：采集上限 650 篇 → 分析上限 80 篇，差距 8×；score 3–4 的 ~500 篇直接丢弃，没有二级索引。
- **Depth C 轮数冲突**：`cli.py` 允许 `--max-rounds 10`，但 `state_machine.py` 硬编码上限 6，10 轮设计无法触达。
- **Zotero 是 Stub，知识"网"缺失**：`references.bib` 已生成需手动导入；`paper-pool.csv` 跨项目索引存在但无可视化；论文"库"有了，节点间关系网络（共引、主题聚类）没有。

详细拆解见 [`plan/future.md §能力上限分析`](./plan/future.md)。

---

## What TrendR is
TrendR 是一个 **research-agent harness**，核心目标是把文献研究流程从一次性生成改造成可恢复、可追踪、可验证的控制面。

## Core Capabilities

### 1. Governed State Machine
普通 workflow 常是一次性生成；TrendR 用显式状态机管理研究流程。  
流程不是“写完即止”，而是按状态推进、带回跳和受控重试。  
核心路径是：`INIT → DISCOVERY → ANALYSIS → GAP_CHECK → WRITING → VERIFY → DONE`。  
这让每一步都可判定、可追踪、可恢复。

### 2. Artifact Contracts
普通 workflow 依赖松散中间文本；TrendR 依赖固定产物契约。  
阶段衔接基于结构化文件，而不是上下文猜测。  
典型产物包括：`candidates.csv`、`matrix.csv`、`gap_report.md`、`review.md`、`verify.json`。  
file contracts 让流程具备可恢复、可调试、可复验的工程边界。

### 3. Independent Verification
普通 workflow 常由同一 agent 自评；TrendR 把生成与验证拆分。  
是否完成由 verifier 判断，不由写作 agent 自我宣布。  
verifier 聚焦三类核心检查：citation consistency、claim support、taxonomy coherence。  
因此“完成”是外部判定结果，而不是生成过程附带的主观结论。

### 4. Recovery and Runtime Portability
普通 workflow 中断后常需整段重跑；TrendR 保留 machine-readable state 与 heartbeat。  
系统可基于 `run_state` 与心跳信息做恢复和观测。  
运行时相关逻辑隔离在 adapter 层，核心状态机不与单一平台耦合。  
这使同一控制逻辑可跨 runtime 复用，而不退化成平台脚本集合。

## Why TrendR is not just a prompt workflow
Most literature-review tools are thin prompt workflows: search, summarize, draft in one pass.  
TrendR turns literature review into a controlled research pipeline with governed states, artifact contracts, independent verification, and resumable execution.  
它的核心不是“写综述”，而是“把研究流程管起来”。

## Workflow vs Harness
- one-shot generation vs governed states
- loose intermediate text vs artifact contracts
- self-check vs independent verifier
- restart from scratch vs resumable execution

## Reliability and Engineering Proof
第三层只证明两件事：系统可靠性、工程可扩展性。

评测指标（仅 5 项）：
- `resume_success_rate`
- `citation_detection_recall / citation_detection_precision`
- `high_relevance_coverage`
- `analysis_fallback_trigger_rate`
- `stable_completion_rate vs single-shot baseline`

Engine 已按 `states / transitions / executors / artifacts / recovery` 分层，`state_machine.py` 只保留协调职责并通过 `step()/run()/resume()` 驱动。

详细说明见：
- [`EVALUATION.md`](./EVALUATION.md)
- [`docs/ENGINE.md`](./docs/ENGINE.md)

## Optional Extensions
扩展层只回答“TrendR 还能接什么、扩到哪里去”。核心身份不变：
- core = recoverable literature review harness
- extension = optional signal intake / integrations

### Platform Hotspots
TrendR also supports multi-platform hotspot collection as an optional signal-intake module. This is not the core product identity.

Use it for:
- topic discovery
- context enrichment
- cross-checking public discussion against academic themes

See [`docs/HOTSPOTS.md`](./docs/HOTSPOTS.md).

### Integrations
TrendR can run with thin adapters and optional external tooling. These integrations extend runtime portability, but they are not the product core.

Use it for:
- runtime portability across supported adapters
- optional toolchain composition around retrieval, bibliography, and storage
- controlled boundary management between core pipeline and external systems

See [`docs/INTEGRATIONS.md`](./docs/INTEGRATIONS.md).

## Roadmap
TrendR is evolving along three tracks:
- better research quality and coverage
- stronger control-plane / recovery / observability
- broader runtime and tool integrations

See [`ROADMAP.md`](./ROADMAP.md).

## 选择你的 Runtime

| 场景 | 推荐 Runtime | 理由 |
|------|------------|------|
| 对话式研究、随时提问 | **Claude Code** ← 推荐 | slash command、subagent、SessionStart 恢复 |
| 代码项目内嵌研究 | **Codex** | `skills/*/codex.md` + `agents/*/codex.md` 与代码上下文直接集成 |
| 每日定时自动化、无人值守 | **OpenClaw** | cron + supervisor 长期运行稳定 |

> 三者共用同一套共享知识文件（`skills/*/SKILL.md`）和状态机（`engine/`），只是 runtime-specific sibling 不同。
> 每个 SKILL.md 内置 Runtime Router，自动休眠非当前 runtime 的指令块：OpenClaw 读 `SKILL.md`，Claude Code 读 `claude-code.md`，Codex 读 `codex.md`。

## Runtime 权威文件

TrendR 这套多 runtime 工作流的关键，不是把一份 prompt 硬塞给所有宿主，而是分成“共享知识 + runtime-specific authority files”：

| 层 | OpenClaw | Claude Code | Codex |
|----|----------|-------------|-------|
| Skill 共享知识 | `skills/*/SKILL.md` | `skills/*/SKILL.md` | `skills/*/SKILL.md` |
| Skill runtime 指令 | 内嵌在 `SKILL.md` | `skills/*/claude-code.md` | `skills/*/codex.md` |
| Agent 共享契约 | `agents/*/CONTRACT.md` | `agents/*/CONTRACT.md` | `agents/*/CONTRACT.md` |
| Agent runtime 指令 | `agents/*/SOUL.md` | `agents/*/claude-code.md` | `agents/*/codex.md` |

自动检测顺序：
- 显式 `--platform` / `TRENDR_PLATFORM` 永远最高优先级
- 否则按 `OPENCLAW_SESSION_ID > CODEX_* > CLAUDE_CODE_* > cli`
- 非当前 runtime 的指令块必须视为 `dormant`

## Quick Start

### Claude Code（推荐 · 互动式研究）

```bash
git clone https://github.com/gy-hou/trendr.git
cd trendr
./install.sh --claude-code        # 安装 agent stubs + slash commands
```

在 Claude Code 中：
```
/tr research "multi-agent trading" --depth B
/tr hotspots
/tr status
/tr resume ~/research/my-project
```

### Codex（代码项目内嵌）

```bash
./install.sh --codex              # 安装到 $CODEX_HOME/skills 或 ~/.codex/skills
python3 cli.py run --topic "agentic RAG" --platform codex
```

或在 Codex 会话中按如下顺序读取：
- `CODEX.md`
- `skills/*/SKILL.md`
- `skills/*/codex.md`
- 需要 agent 行为时再读 `agents/*/codex.md`

### OpenClaw（每日自动化 · 定时任务）

```bash
./install.sh --openclaw           # 注册 agents 到 ~/.openclaw/
# 配置每日 cron / launchd（见 plan/future.md §每日定时方案）
openclaw agent --agent review-lead --message "daily hotspots scan"
```

> 如需 Claude Code 无人值守定时运行，见 [`plan/future.md`](./plan/future.md)。

最小输入要求：
- `--topic`：研究主题
- `--platform`：运行时（Claude Code 环境下自动检测，无需显式指定）

See [`docs/USAGE.md`](./docs/USAGE.md).

## 安装落点

不同 runtime 的 installer 会写到不同位置：

| Runtime | 安装命令 | 落点 |
|---------|----------|------|
| Claude Code | `./install.sh --claude-code` | 仓库 `.claude/` 或 `~/.claude/`，以及 `.claude-plugin/` |
| Codex | `./install.sh --codex` | `${CODEX_HOME:-~/.codex}/skills` |
| OpenClaw | `./install.sh --openclaw` | `~/.openclaw/workspace/agents` 与 `~/.openclaw/workspace/skills` |

对应卸载：

```bash
./uninstall.sh --claude-code
./uninstall.sh --codex
./uninstall.sh --openclaw
```

## Run Modes
- `basic`：标准文献综述流水线入口（默认）。
- `full`：在标准流水线基础上启用额外流程（适合完整运行场景）。
- `lite`：轻量模式，适合最小操作路径或配合独立热点命令。

See [`docs/USAGE.md`](./docs/USAGE.md).

## Outputs
- `candidates.csv`：候选论文池。
- `matrix.csv`：结构化分析矩阵。
- `gap_report.md`：覆盖缺口与回跳依据。
- `review.md`：综述正文。
- `verify.json`：独立验证结果。
- `run_state.json`：机器可读运行状态。
- `heartbeat.json`：运行心跳与活性信息。

See [`docs/OUTPUTS.md`](./docs/OUTPUTS.md).

## Reproduce Evaluation
```bash
python3 eval/scripts/run_eval.py --mode trendr --execute
python3 eval/scripts/run_eval.py --mode baseline
python3 eval/scripts/summarize_eval.py
```

查看结果：
- `eval/results/summary_table.md`
- `eval/results/failure_cases.md`

See [`EVALUATION.md`](./EVALUATION.md).

## Troubleshooting
常见排查入口：
- 运行中断恢复：先看 `run_state.json`，再执行 `python3 cli.py resume <project_dir> --platform <runtime>`。
- 缺少 artifact：对照 `run_state.json.current_state` 与 `progress.md` 判断卡在哪个阶段。
- 验证未通过：查看 `verify.json` 的 `issues` 和各检查项。
- fallback 触发：查看 `logs/latest.log` 和阶段 history。
- runtime/adapter 异常：先看 `heartbeat.json`、`run_state.json`、CLI stderr。

See [`docs/TROUBLESHOOTING.md`](./docs/TROUBLESHOOTING.md).

## Reference Docs
- [`docs/USAGE.md`](./docs/USAGE.md)
- [`docs/OUTPUTS.md`](./docs/OUTPUTS.md)
- [`docs/TROUBLESHOOTING.md`](./docs/TROUBLESHOOTING.md)
- [`docs/REFERENCE.md`](./docs/REFERENCE.md)
- [`docs/CLAUDE_CODE_ADAPTER.md`](./docs/CLAUDE_CODE_ADAPTER.md)
- [`plan/future.md`](./plan/future.md) — Claude Code 每日 cron 自动化方案
- [`EVALUATION.md`](./EVALUATION.md)
- [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- [`ROADMAP.md`](./ROADMAP.md)

## License
MIT
