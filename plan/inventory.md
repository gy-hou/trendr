# TrendR Runtime Inventory（phase 0 审计）

生成日期：2026-04-17

---

## 1. OpenClaw 耦合点

### 1.1 `openclaw` / `OpenClaw` 符号

| 文件 | 行 | 说明 |
|------|-----|------|
| `cli.py` | 5, 29, 77-79, 91-169, 249-276, 438-465 | `PLATFORM_CHOICES` 含 `openclaw`；`load_openclaw_config`、`validate_openclaw_agent_registry`、`validate_openclaw_agent_auth`、`_resolve_openclaw_agent_primary_model` 等专属函数；`cmd_run`/`cmd_resume` 里 openclaw 分支校验 |
| `engine/state_machine.py` | 54, 561, 625 | `OpenClawAdapter()` 硬实例化；`bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh` 路径；browser_eval 分支 |
| `engine/adapters/openclaw.py` | 全文 | OpenClaw 专属适配器（`sessions_spawn`/`sessions_yield`/`browser_eval`） |
| `install.sh` | 27, 163, 395-396, 752-819 | banner 文案、`WORKSPACE` 变量、`exec:` 调用 supervisor.py、`exec:` 注册 agent 等 |
| `uninstall.sh` | 6, 40-41, 46 | `OPENCLAW_WORKSPACE` 变量；清理提示引用 `~/.openclaw/openclaw.json` |
| `CLAUDE.md` | 4, 9, 50-64 | 描述 OpenClaw 等价映射 |
| `AGENTS.md` | 4, 9, 73, 84-95 | OpenClaw 工具名映射 |
| `ARCHITECTURE.md` | 28, 38, 42, 216, 294, 300, 339, 349, 584, 614, 666, 704-811 | 设计文档中大量 OpenClaw 引用 |
| `REVIEW.md` | 20, 41, 51-52, 63-64, 85, 92, 118 | 评审文档提及平台锁定 |
| `protocols/research-team-protocol.md` | 40 | `~/Documents/OpenClaw-Vault/Research/` |
| `protocols/trendr-protocol.md` | 9 | 提到不写入 `OpenClaw-Vault` |
| `ROADMAP.md` | 34 | "deeper OpenClaw runtime alignment" |

### 1.2 `sessions_spawn` / `sessions_yield`

| 文件 | 行 | 说明 |
|------|-----|------|
| `agents/review-lead/SOUL.md` | 21, 42, 106-131 | 子 agent 派发核心逻辑 |
| `engine/adapters/openclaw.py` | 119, 129, 219 | `spawn_agent` 实现（`sessions_spawn` + `sessions_yield`） |
| `install.sh` | 582, 780-800 | 安装时注入 `sessions_yield`/`sessions_spawn` 到 agent SOUL |
| `ARCHITECTURE.md` | 38, 302, 764 | 设计文档提及 |
| `AGENTS.md` / `CLAUDE.md` | 93-94, 61-62 | 工具映射说明 |

**处理建议**：phase 1 的 `ClaudeCodeAdapter` 用 `claude_code_dispatch.jsonl` + completion 文件代替；`SOUL.md` 不动，在 `agents/<name>/claude-code.md` 里改用 `Agent` 工具。

### 1.3 `web_fetch:` 语法

| 文件 | 行（示例） | 说明 |
|------|-----------|------|
| `skills/paper-scout/SKILL.md` | 228-326 | 大量 `web_fetch: { url: ... }` 学术 API 调用 |
| `skills/paper-analyzer/SKILL.md` | 31-46 | 论文详情抓取 |
| `skills/review-writer/SKILL.md` | 27 | `exec: ls ...`（review-writer 主要用 exec:） |
| `engine/adapters/openclaw.py` | 6 | 注释说明 `http_get → web_fetch:` |

**处理建议**：phase 2 在 `skills/<name>/claude-code.md` 里用 `WebFetch` 工具替换；原 `SKILL.md` 内的 `web_fetch:` 指令保留。

### 1.4 `exec:` 语法

| 文件 | 行（示例） | 说明 |
|------|-----------|------|
| `skills/paper-scout/SKILL.md` | 80-83, 141, 378, 465-471 | Chrome CDP 启动、mkdir、sleep 等 |
| `skills/review-writer/SKILL.md` | 27 | `exec: ls ~/research/[PROJECT]/notes/` |
| `skills/trendr-watchdog/SKILL.md` | 48, 68, 85 | 启动/停止 watchdog 进程 |
| `skills/research-vault/SKILL.md` | 54-231 | Obsidian vault 操作 |
| `agents/review-lead/SOUL.md` | 53, 61-62, 150 | mkdir, watchdog 启动/停止 |
| `install.sh` | 395-396, 752-819 | context7、mkdir、supervisor.py 启动 |

**处理建议**：phase 2 在 `claude-code.md` 里用 `Bash` 工具替换；原 `SKILL.md` 内的 `exec:` 保留。

### 1.5 `supervisor.py`（OpenClaw 注入式 watchdog）

| 文件 | 行 | 说明 |
|------|-----|------|
| `skills/trendr-watchdog/SKILL.md` | 15, 28, 48-50 | 核心守夜逻辑，`openclaw agent --session-id` 注入 |
| `agents/review-lead/SOUL.md` | 22, 39, 61 | 启动 supervisor.py 的逻辑 |
| `install.sh` | 766 | 安装时写入 supervisor.py 启动命令到 SOUL |
| `engine/recovery/watchdog.py` | （存在） | `engine/recovery/` 下有 `watchdog.py`、`heartbeat.py`、`resume.py` |

**处理建议**：phase 6 在 `runtimes/claude-code/hooks/` 新增三个 hook 脚本替代；`supervisor.py` 原地不动。

### 1.6 `OPENCLAW_SESSION_ID` / `OPENCLAW_*` 环境变量

| 文件 | 行 | 说明 |
|------|-----|------|
| `engine/runtime.py` | 35, 45 | `detect_runtime` 优先级第 2 位（现为 OpenClaw 优先） |
| `tests/test_cli_adapter.py` | 243, 253, 360, 405 | 测试用例中使用该变量 |
| `cli.py` | 33 | `TRENDR_OPENCLAW_AGENTS` 常量 |
| `uninstall.sh` | 6 | `OPENCLAW_WORKSPACE` 变量 |
| `install.sh` | 163 | `OPENCLAW_WORKSPACE` 变量 |
| 全部 `skills/*/SKILL.md` | ~17 | 运行时识别优先级说明 |

**处理建议**：phase 8 改优先级（`CLAUDE_CODE_*` 上移到 `OPENCLAW_SESSION_ID` 之前）；当前维持不变。

### 1.7 `~/.openclaw` 配置目录

| 文件 | 行 | 说明 |
|------|-----|------|
| `cli.py` | 93, 162, 260, 276 | `~/.openclaw/openclaw.json` 路径；`openclaw gateway restart` 提示 |
| `install.sh` | 163 | `WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"` |
| `uninstall.sh` | 6, 40-41 | 清理提示 |

**处理建议**：phase 5 新建 `runtimes/openclaw/install.sh` 继承，`runtimes/claude-code/install.sh` 不引用此路径。

### 1.8 `browser --browser-profile cdp`（OpenClaw 浏览器 CLI）

| 文件 | 行（示例） | 说明 |
|------|-----------|------|
| `skills/platform-hotspots/SKILL.md` | 52, 66-450 | Zhihu、X、Reddit、YouTube、GitHub、HN、ProductHunt 等 CDP 采集 |
| `skills/paper-scout/SKILL.md` | 106-109 | arXiv CDP 搜索 |
| `skills/chrome-cdp-setup/SKILL.md` | 179-182 | CDP 操作示例 |
| `engine/adapters/openclaw.py` | 7 | `browser_eval → openclaw browser --browser-profile cdp eval` |

**处理建议**：phase 2 在 `skills/platform-hotspots/claude-code.md` 和 `skills/paper-scout/claude-code.md` 里用 MCP chrome server / `WebFetch` / `WebSearch` 按优先顺序处理；无法抓取时标 `skipped_with_reason`。

---

## 2. Claude Code 侧已具备的能力

| 能力 | 位置 | 备注 |
|------|------|------|
| `_call_claude_cli` subprocess 路径 | `engine/adapters/cli.py` | 已实现 Claude CLI subprocess 调用；phase 1 的 `ClaudeCodeAdapter` 的 subprocess 模式可复用 |
| `detect_runtime` 含 `CLAUDE_CODE_*` 分支 | `engine/runtime.py:51` | 已实现但优先级低于 OpenClaw；phase 8 翻转 |
| `PLATFORM_CHOICES` 含 `claude-code` / `claudecode` | `cli.py:29` | 入口已支持 claude-code 参数 |
| `cli.py` routing 到 `CLIAdapter` when `claude-code` | `cli.py:77-86` | 当前 `claude-code` fallthrough 到 `CLIAdapter`；phase 1 改为 `ClaudeCodeAdapter` |
| `CLAUDE.md` 工具映射表 | `CLAUDE.md:54-64` | 完整的 OpenClaw → Claude Code 工具对照表，作为 phase 2 的输入 |
| `engine/recovery/` 目录 | `engine/recovery/{heartbeat,resume,retries,watchdog}.py` | 已有 4 个恢复工具；phase 6 新增 `claude_code_resume.py` |
| 无 `runtimes/` 目录 | — | 尚未创建，phase 5 新建 |
| 无 `agents/<name>/claude-code.md` | — | 尚未创建，phase 3 新建 |
| 无 `skills/<name>/claude-code.md` | — | 尚未创建，phase 2 新建 |

---

## 3. Claude Code 需新增的资产（权威源路径）

| 类型 | 权威源路径（仓库内） | 安装产物 | 负责 Phase |
|------|---------------------|----------|-----------|
| ClaudeCodeAdapter | `engine/adapters/claude_code.py` | — | 1 |
| Skill 指令（Claude Code） | `skills/<name>/claude-code.md` × 8 | 原地读取（无需生成） | 2 |
| Runtime Router 段 | `skills/<name>/SKILL.md`（顶部新增小节） | — | 2 |
| Subagent body（Claude Code） | `agents/<name>/claude-code.md` × 4 | `.claude/agents/<name>.md`（软链） | 3 |
| Slash command 模板 | `runtimes/claude-code/commands/tr.md` + `tr/*.md` × 5 | `.claude/commands/tr[/*].md`（渲染后） | 4 |
| Render script | `runtimes/claude-code/render-commands.sh` | — | 4 |
| Plugin manifest（权威源） | `runtimes/claude-code/plugin.json` | `.claude-plugin/plugin.json`（软链） | 5 |
| Claude Code installer | `runtimes/claude-code/install.sh` | — | 5 |
| Claude Code uninstaller | `runtimes/claude-code/uninstall.sh` | — | 5 |
| OpenClaw installer（搬迁） | `runtimes/openclaw/install.sh` | — | 5 |
| OpenClaw uninstaller（搬迁） | `runtimes/openclaw/uninstall.sh` | — | 5 |
| Hooks | `runtimes/claude-code/hooks/{session_start,stop_heartbeat,subagent_stop}.py` | 原路径被 settings.json 引用 | 6 |
| Settings 示例 | `runtimes/claude-code/settings.json.example` | 供用户 merge 入 `~/.claude/settings.json` | 6 |
| Resume utility | `engine/recovery/claude_code_resume.py` | — | 6 |
| Watchdog Claude Code 描述 | `skills/trendr-watchdog/claude-code.md` | — | 6 |
| 契约测试 | `tests/test_claude_code_adapter.py`、`test_claude_code_skill_contracts.py`、`test_plugin_manifest.py`、`test_runtime_isolation.py` | — | 7 |
| E2E smoke | `tests/e2e/test_claude_code_smoke.py` | — | 7 |
| CI workflow | `.github/workflows/ci.yml` | — | 7 |

---

## 4. 风险条目（后续 phase 需关注）

- **R-1**：`~/research/{project}/run_state.json` 同时被 Python 状态机和 Claude Code agent 读写，需保证文件锁或单写者（phase 1 设计原子写）。
- **R-2**：Claude Code 的 `Agent` tool 默认并行，OpenClaw adapter 是同步的；phase 1 要显式约束并发数，防止重复派发。
- **R-3**：`skills/*/SKILL.md` 的 `web_fetch:` 指令被现有 OpenClaw 用户依赖，不能删除——只新增，不替换。
- **R-4**：`cli.py` 里大量 OpenClaw 专属函数（`load_openclaw_config`、`validate_openclaw_agent_registry` 等）；phase 1 只在 `claude-code` 分支路由到新 adapter，不删除现有函数。
- **R-5**：`engine/state_machine.py:54` 硬实例化 `OpenClawAdapter()`；phase 1 改为 `get_adapter(platform)` 工厂调用，不破坏已有 OpenClaw 路径。
- **R-6**：`runtimes/claude-code/hooks/` 中的脚本需要标准库可用（不依赖 pip 安装），且不能阻塞 Claude Code 会话启动（try/except 兜底 + 静默退出 0）。
- **R-7**（phase 8）：翻转 `CLAUDE_CODE_*` 优先级后，同时设置 `CLAUDE_CODE_*` 和 `OPENCLAW_SESSION_ID` 的用户会自动切到 claude-code；release notes 需提示 `TRENDR_PLATFORM=openclaw` 覆盖方式。

---

## 5. 改动影响面统计

| 文件 | 预计改动 Phase | 是否破坏 OpenClaw |
|------|--------------|-----------------|
| `engine/adapters/claude_code.py` | 1（新增） | 否 |
| `engine/adapters/cli.py` | 1（minor，routing） | 否 |
| `cli.py` | 1, 5, 8 | 否（条件分支） |
| `engine/state_machine.py` | 1（工厂 call 替换） | 否（OpenClaw 路径不变） |
| `engine/runtime.py` | 8（优先级翻转） | 是（phase 8 前兼容） |
| `skills/*/SKILL.md` | 2（只加 Runtime Router 小节） | 否 |
| `skills/*/claude-code.md` | 2（新增兄弟文件 × 8） | 否 |
| `agents/*/claude-code.md` | 3（新增 × 4） | 否 |
| `agents/*/CONTRACT.md` | 3（可选，新增 × 4） | 否 |
| `runtimes/claude-code/**` | 4/5/6（全新目录） | 否 |
| `runtimes/openclaw/install.sh` | 5（从顶层搬迁，逻辑不变） | 否 |
| `install.sh` | 5（改为 dispatcher） | 否（无 flag 默认仍走 openclaw，直到 phase 8） |
| `uninstall.sh` | 5（改为 dispatcher） | 否 |
| `engine/recovery/claude_code_resume.py` | 6（新增） | 否 |
| `tests/test_claude_code_adapter.py` | 1（新增） | 否 |
| 新增测试文件 × 4 | 7 | 否 |
| `.github/workflows/ci.yml` | 7（新增） | 否 |
| `CLAUDE.md` | 8（文案调整） | 否 |
| `README.md` / `README_EN.md` | 8 | 否 |
| `pyproject.toml` / `plugin.json` | 8（版本 2.1.0） | 否 |
