# Phase 0 — 现状审计与差距映射

> 遵循 [`plan/structure.md`](./structure.md)（整体 layout）与 [`plan/README.md`](./README.md)（通用规则）。
> 本 phase 不写任何业务代码，只输出清单与差距表。完成后产出：
> - `plan/inventory.md`（所有 OpenClaw 耦合点 + 可分离到 `runtimes/claude-code/` 的对应项）
> - `plan/STATUS.md`（初版状态文件，后续每个 phase 都要更新）
>
> 目的：给后续 phase 一份"地图"。phase 1 之后所有改动都要引用这里的条目编号。

## 目标

1. 列全 TrendR 仓库里和 runtime 挂钩的所有文件与符号。
2. 对每个耦合点给出 Claude Code 侧的替换策略（native tool、hooks、agent 调用等）。
3. 输出一份后续 phase 可按编号引用的 inventory。
4. 创建 `plan/STATUS.md`，初始化迁移追踪。

## 前置检查

- 本仓库位于 `/Users/mac/Documents/GitHub/trendr`。
- 分支 `main`，`git status` 干净（有未提交改动时先 commit 或 stash）。
- 以下文件/目录存在：`cli.py`、`engine/`、`skills/`、`agents/`、`install.sh`、`CLAUDE.md`。

## 步骤

### 0.1 采集 OpenClaw 耦合点

使用 Grep 工具（不要用 bash grep）把以下模式匹配全仓库：

| 模式 | 含义 | 处理建议 |
|------|------|---------|
| `openclaw` / `OpenClaw` | 运行时名、包名、二进制名 | phase 1/5 新增 Claude Code 等价物 |
| `sessions_spawn` / `sessions_yield` | subagent RPC | phase 1 用 `Agent` tool 替换 |
| `web_fetch:` / `web_fetch {` | OpenClaw 抓取语法 | phase 2 补 `WebFetch` 指令块 |
| `exec:` | OpenClaw shell 语法 | phase 2 补 `Bash` 指令块 |
| `supervisor.py` | OpenClaw 注入式 watchdog | phase 6 用 Claude Code hooks 替换 |
| `OPENCLAW_SESSION_ID` / `OPENCLAW_` 环境变量 | runtime 探测 | phase 8 改优先级 |
| `~/.openclaw` | OpenClaw 配置目录 | phase 5 installer 分支 |
| `browser --browser-profile cdp` | OpenClaw 浏览器 CLI | phase 2 补 MCP browser/`WebFetch` 方案 |

对每个模式运行一次 Grep，把命中路径写进 `plan/inventory.md` 对应小节。

### 0.2 采集 Claude Code 侧"已有但未启用"的能力

在 `inventory.md` 单独一节列出：
- `engine/adapters/cli.py` 已有的 `_call_claude_cli`（subprocess 路径）— 后续是否保留？
- `engine/runtime.py` 的 `detect_runtime` 优先级（现为 OpenClaw 优先）。
- `CLAUDE.md` 已描述的 OpenClaw ↔ Claude Code 工具映射表 — 作为 phase 2 的输入。
- `cli.py::PLATFORM_CHOICES` 已包含 `claude-code` / `claudecode`。

### 0.3 列出 Claude Code 端需新增的资产（权威源路径）

在 `inventory.md` 加一节 "Claude Code 权威源清单"。注意：`.claude/` 和 `.claude-plugin/` 是 **installer 生成的产物**，权威源在 `runtimes/claude-code/` 或 `agents/<name>/claude-code.md`。

| 类型 | 权威源路径（仓库内） | 安装产物（由 installer 放置） | 说明 |
|------|---------------------|-----------------------------|------|
| Subagent body | `agents/<name>/claude-code.md` × 4 | `.claude/agents/<name>.md`（软链或拷贝）| phase 3 |
| Skill 指令 | `skills/<name>/claude-code.md` × 8 | 原地被 Claude Code 读取（无需生成）| phase 2 |
| Slash command 模板 | `runtimes/claude-code/commands/tr[/*].md` | `.claude/commands/tr[/*].md`（渲染 `{{repo_root}}` 后）| phase 4 |
| Plugin manifest | `runtimes/claude-code/plugin.json` | `.claude-plugin/plugin.json`（软链）| phase 5 |
| Hooks | `runtimes/claude-code/hooks/*.py` | 原路径被 settings.json 引用 | phase 6 |
| Settings 示例 | `runtimes/claude-code/settings.json.example` | 供用户拷贝到 `~/.claude/settings.json` | phase 6 |
| Installer | `runtimes/claude-code/install.sh` / `uninstall.sh` | 由顶层 `install.sh --claude-code` 调用 | phase 5 |

### 0.4 产出 `plan/STATUS.md`

使用以下模板（Sonnet 每完成一个 phase 就来更新此表）：

```markdown
# TrendR → Claude Code 迁移状态

最后更新：YYYY-MM-DD by phase-N

| Phase | 状态 | commit | 备注 |
|-------|------|--------|------|
| 0 | 进行中 / 已完成 | `<sha>` |  |
| 1 | 待开始 | - |  |
| 2 | 待开始 | - |  |
| 3 | 待开始 | - |  |
| 4 | 待开始 | - |  |
| 5 | 待开始 | - |  |
| 6 | 待开始 | - |  |
| 7 | 待开始 | - |  |
| 8 | 待开始 | - |  |

## 遗留 TODO

- (empty)

## 回滚指引

- phase N 回滚：`git revert <sha>`，再把 `STATUS.md` 表里该 phase 的状态改回"待开始"。
```

### 0.5 产出 `plan/inventory.md`

骨架如下：

```markdown
# TrendR Runtime Inventory（phase 0 审计）

生成日期：YYYY-MM-DD

## 1. OpenClaw 耦合点

### 1.1 `openclaw` / `OpenClaw` 符号
- `path:line` — 上下文 1 行
- …

### 1.2 `sessions_spawn` / `sessions_yield`
…

### 1.3 `web_fetch:` 语法
…

（按 0.1 表格逐项）

## 2. Claude Code 侧已具备的能力

- …

## 3. Claude Code 需新增的资产

（按 0.3 表格）

## 4. 风险条目（后续 phase 需关注）

- R-1: `~/research/{project}/run_state.json` 同时被 Python 状态机和 Claude Code agent 读写，需保证文件锁或单写者。
- R-2: Claude Code 的 `Agent` tool 默认并行，OpenClaw adapter 是同步的；phase 1 要显式约束并发数。
- R-3: skill 的 `web_fetch:` 指令被现有 OpenClaw 用户依赖，不能删除。

## 5. 改动影响面统计

| 文件 | 预计改动 phase | 是否破坏 OpenClaw |
|------|-------------|------------------|
| engine/runtime.py | 8 | 是（phase 8 改优先级前兼容）|
| engine/adapters/cli.py | 1 | 否 |
| cli.py | 1, 5, 8 | 否（条件分支）|
| skills/*/SKILL.md | 2 | 否（只加 Runtime Router，内容保持 OpenClaw 可读）|
| skills/*/claude-code.md | 2 | 否（新增兄弟文件）|
| skills/*/openclaw.md | 2（可选）| 否（若拆分，SKILL.md 对应段要改 "见 openclaw.md"）|
| agents/*/SOUL.md | 3 | 否（不动，新增 `agents/*/claude-code.md` 兄弟）|
| runtimes/claude-code/** | 4/5/6 | 否（全新目录）|
| runtimes/openclaw/install.sh | 5 | 否（只是从顶层 install.sh 搬过来，逻辑不变）|
| install.sh | 5 | 否（变成 dispatcher，无 flag 默认仍走 openclaw）|
```

## 验收

- `plan/inventory.md` 存在，涵盖 0.1 表格每一行。
- `plan/STATUS.md` 存在，phase 0 状态为 `已完成`。
- `git diff --name-only` 只包含 `plan/*` 新文件，无其它代码改动。
- `python -c "import engine.runtime; print(engine.runtime.detect_runtime({}))"` 输出 `cli`（证明代码完整）。

## 风险与回滚

- 本 phase 只新增文档。回滚直接删除 `plan/inventory.md` 和 `plan/STATUS.md` 即可。
- 若 grep 漏掉某个耦合点，后续 phase 发现时补录进 `inventory.md` 的 "补丁" 小节，不重写。

## 不在本 phase 做的事

- 不动任何 `engine/`、`skills/`、`agents/`、`cli.py`。
- 不创建 `.claude/` 目录。
- 不改任何 OpenClaw 行为。
