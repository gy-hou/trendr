# Phase 4 — Slash Commands 模板（`runtimes/claude-code/commands/`）

> 遵循 [`plan/structure.md`](./structure.md) §1 / §3.3。
> 产出：`runtimes/claude-code/commands/` 下 6 个 slash 命令模板（含 `{{repo_root}}` 占位符）。Installer（phase 5）负责渲染到 `.claude/commands/`。
> 目标：用户在 Claude Code 里输入 `/tr research "topic"` / `/tr hotspots` / `/tr status` / `/tr resume` / `/tr template` 直接触发。
> 依赖 phase：0、1。与 phase 2 / 3 并行安全。

## 目录结构

```
runtimes/claude-code/commands/
├── tr.md            # 入口，help / 分派
└── tr/
    ├── research.md
    ├── hotspots.md
    ├── status.md
    ├── resume.md
    └── template.md
```

**这是模板源**。安装时 installer 把 `{{repo_root}}` 替换成实际仓库路径后写入：
- 项目安装：`<repo>/.claude/commands/tr[/*].md`
- 用户安装：`~/.claude/commands/tr[/*].md`

## 命令设计（与 `cli.py` 子命令对齐）

### 4.1 `/tr research`

文件：`runtimes/claude-code/commands/tr/research.md`

```markdown
---
description: "Run a full TrendR literature-review pipeline"
argument-hint: "\"<topic>\" [--depth A|B|C] [--profile basic|full] [--project-dir PATH]"
allowed-tools: Bash, Read, Write, Agent
---

Run TrendR's v2 state machine on the topic in `$ARGUMENTS`.

Steps (execute literally):

1. Parse `$ARGUMENTS`: first quoted/positional token = topic. Optional flags:
   `--depth` (default B), `--profile` (default basic), `--project-dir`, `--time-budget`.
2. Ensure env: `TRENDR_PLATFORM=claude-code` and, when inside Claude Code, `TRENDR_CC_MODE=native`.
3. Invoke via Bash (non-blocking — use background if needed):
   `TRENDR_PLATFORM=claude-code python {{repo_root}}/cli.py run --topic "<topic>" --depth <DEPTH> --profile <PROFILE> --project-dir <DIR> --platform claude-code --no-watchdog`
4. While the state machine runs, poll `<DIR>/claude_code_dispatch.jsonl` and satisfy
   each dispatched op. For every line:
   - `op=agent` → spawn the named subagent via `Agent` tool, then write
     `<DIR>/claude_code_completions/<handle>.json`.
   - `op=webfetch` → call `WebFetch` and write completion.
   - `op=bash` → call `Bash` and write completion.
5. After exit, read `<DIR>/run_state.json`, report final state + artifacts
   (`review.md`, `references.bib`, `matrix.csv`, `verify.json`).
6. If `verify.json.overall_status != "passed"`, summarize failures.

Do not fabricate artifacts. Do not skip dispatch polling — the state machine
depends on Claude Code completing each dispatched op.
```

### 4.2 `/tr hotspots`

文件：`runtimes/claude-code/commands/tr/hotspots.md`

```markdown
---
description: "Collect cross-platform AI hotspots via TrendR Lite"
argument-hint: "[--topic \"<label>\"] [--per-source-limit N]"
allowed-tools: Bash, Read, Write, WebFetch, WebSearch, Agent
---

Run TrendR Lite hotspots:

1. Parse `$ARGUMENTS`. Default topic = "AI agents and LLM ecosystem".
2. Invoke: `TRENDR_PLATFORM=claude-code python {{repo_root}}/cli.py hotspots <flags>`
3. For JS-heavy sources the runner requests page evaluations. In Claude Code, use
   this priority: MCP chrome server → `WebFetch` (static) → `WebSearch` → mark
   the source `skipped_with_reason`.
4. After completion, summarize top items per platform from
   `<DIR>/hotspots_summary.md` + `hotspots_report.md`.
```

### 4.3 `/tr status`

文件：`runtimes/claude-code/commands/tr/status.md`

```markdown
---
description: "Show status of the latest TrendR run"
argument-hint: "[project-dir]"
allowed-tools: Bash, Read
---

1. If `$ARGUMENTS` empty, find latest via:
   `ls -td ~/research/*/run_state.json 2>/dev/null | head -1`
2. Invoke: `python {{repo_root}}/cli.py status <project-dir>`
3. Echo last 20 lines of `progress.md` and the latest `heartbeat.json`.
```

### 4.4 `/tr resume`

文件：`runtimes/claude-code/commands/tr/resume.md`

```markdown
---
description: "Resume a paused or failed TrendR run"
argument-hint: "<project-dir>"
allowed-tools: Bash, Read, Write, Agent
---

1. Validate `<project-dir>/run_state.json` exists and `version == 2`.
2. Invoke: `TRENDR_PLATFORM=claude-code python {{repo_root}}/cli.py resume <project-dir> --platform claude-code`
3. Poll dispatch + satisfy ops like `/tr research`.
4. Summarize outcome.
```

### 4.5 `/tr template`

文件：`runtimes/claude-code/commands/tr/template.md`

```markdown
---
description: "Initialize TrendR hotspots template + private config"
argument-hint: "[--force]"
allowed-tools: Bash
---

Run: `python {{repo_root}}/cli.py hotspots-template $ARGUMENTS`
Report the two paths written; remind the user the private file must not be
committed.
```

### 4.6 入口 `/tr`

文件：`runtimes/claude-code/commands/tr.md`

```markdown
---
description: "TrendR dispatcher — run research, hotspots, status, resume"
argument-hint: "<subcommand> ..."
allowed-tools: Bash
---

Route `$1` to `.claude/commands/tr/<sub>.md`:
research | hotspots | status | resume | template.
If `$1` empty or `help`, print the subcommand list.
```

## `{{repo_root}}` 渲染

Slash command 文件本身不知道仓库根。约定：
- 模板里用 `{{repo_root}}` 占位。
- Installer（phase 5 `runtimes/claude-code/install.sh`）用真实路径替换后写入目标目录。
- 本 phase 提供开发期辅助脚本 `runtimes/claude-code/render-commands.sh`：
  - 无参数：`--dst .claude/commands --repo-root $(git rev-parse --show-toplevel)`
  - `--user`：`--dst ~/.claude/commands`
  - `--dry-run`：只打印将写的路径与替换后的首 10 行。
  - 实现：简单 `sed -e "s|{{repo_root}}|${ROOT}|g"`，遍历 `runtimes/claude-code/commands/**/*.md`。

## 步骤

1. 新建 `runtimes/claude-code/commands/` 目录。
2. 按 4.1-4.6 写 6 个模板文件。
3. 新建 `runtimes/claude-code/render-commands.sh`（`chmod +x`）。
4. Dry-run 冒烟：`bash runtimes/claude-code/render-commands.sh --dry-run`，打印 6 个目标路径与预期替换后内容。
5. 不真正写 `.claude/commands/`（由 phase 5 installer 做）。如果本地确实想立刻用，允许手动跑渲染脚本，但不 commit `.claude/commands/` 下的文件（加到 `.gitignore`）。
6. 更新 `.gitignore`：`.claude/commands/`（防止手动渲染被误提交）。注意**不要** 忽略 `.claude/agents/`（phase 3 / 5 决定它是提交产物 or 软链产物；本 phase 先保守不碰）。
7. 更新 `plan/STATUS.md` phase 4。

## 验收

- [ ] `runtimes/claude-code/commands/tr.md` + 5 个 `tr/*.md` 存在，frontmatter 合法。
- [ ] `runtimes/claude-code/render-commands.sh` 可执行；`--dry-run` 退出码 0 且输出含 6 个目标路径。
- [ ] 模板里 `{{repo_root}}` 出现次数匹配（每个命令至少 1 次或 0 次，不多不少）：`grep -rn '{{repo_root}}' runtimes/claude-code/commands/` 输出齐整。
- [ ] `.gitignore` 新增 `.claude/commands/` 一行。
- [ ] `plan/STATUS.md` phase 4 勾选。

## 风险

- R-1（用户 `$ARGUMENTS` 里有引号 / 空格）：命令 body 显式说明"第一个带引号 token 是 topic"；Claude Code 会按 shell 词法解释。
- R-2（Bash 调用触发权限提示）：phase 6 `settings.json.example` 把 `Bash(python:*)` 加 allow。
- R-3（渲染脚本路径含空格）：`sed` 用 `|` 作分隔符避免 `/` 冲突；路径用双引号包裹。
- 回滚：`git revert` + 删 `runtimes/claude-code/commands/` 与 `runtimes/claude-code/render-commands.sh` + 回退 `.gitignore`。

## 不做的事

- 不写 plugin 清单（phase 5）。
- 不改 CLI Python 代码。
- 不写 hooks（phase 6）。
- 不动 OpenClaw 相关脚本。
