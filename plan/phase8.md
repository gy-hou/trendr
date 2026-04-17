# Phase 8 — 切换 Claude Code 为主 Runtime

> 遵循 [`plan/structure.md`](./structure.md)（路径约定不变，仅翻转默认优先级与文档主 runtime）。
> 产出：`engine/runtime.py` 优先级调整、`install.sh` 交互菜单默认选项翻转、README/README_EN/CLAUDE.md/ARCHITECTURE/ROADMAP 文档改写、版本号冲到 2.1.0、release notes。
> 目标：Claude Code 成为 TrendR 默认且推荐的 runtime；OpenClaw 降为"长期支持兼容"，但文件与路径依然存在、随时可被唤醒。
> 依赖 phase：1-7 全部完成并合入 main。

## 前置条件（必须满足）

- phase 1-7 的所有 commit 都已合入 `main`。
- `python -m pytest tests/ -q` 全绿。
- 至少一次人工在 Claude Code 下跑通 `/tr research "<topic>" --depth A --profile basic` 并产出 `review.md` + `verify.json`（记录在 `plan/STATUS.md` 的"验收回执"）。
- 至少一次在 OpenClaw 下跑通 `openclaw agent --agent review-lead --message "..."`，确认 OpenClaw 路径未回退（如无 OpenClaw 环境，至少让 `tests/test_openclaw_adapter.py` 全绿）。

## 改动清单

### 8.1 runtime 优先级（`engine/runtime.py`）

当前：
```python
# detect_runtime priority:
# 1) TRENDR_PLATFORM
# 2) OPENCLAW_SESSION_ID
# 3) CODEX_*
# 4) CLAUDE_CODE_*
# 5) cli
```

改为：
```python
# 1) TRENDR_PLATFORM           # 用户显式
# 2) CLAUDE_CODE_*             # Claude Code env
# 3) OPENCLAW_SESSION_ID       # OpenClaw 兼容
# 4) CODEX_*
# 5) cli
```

对应代码改动：`detect_runtime` 的 `if any(k.startswith("CLAUDE_CODE_") for k in source): return "claude-code"` 上移到 `OPENCLAW_SESSION_ID` 检查之前。

### 8.2 `cli.py::PLATFORM_CHOICES` 与文档顺序

把 `claude-code` 放到数组第一位：
```python
PLATFORM_CHOICES = ["claude-code", "openclaw", "codex", "claudecode", "cli"]
```

`cmd_run` / `cmd_resume` 的帮助文本示例里默认示例改为：
```
python cli.py run --topic "RL multi-agent" --platform claude-code
```

### 8.3 `CLAUDE.md`（项目指令）

- Runtime Contract 小节：调顺序到 `claude-code` 第一，附 " 现为主 runtime" 说明。
- Workflow 示例：默认示例用 Claude Code（slash command + `Agent` 工具）。
- OpenClaw 块移到 "Compatibility" 小节，标明 "兼容维持，不再主推"。

### 8.4 `README.md` / `README_EN.md`

- 顶部 banner 改为 "Claude Code–first research harness"。
- Quick start：
  1. `claude /plugin install trendr`（占位，若 marketplace 未上，退回 `./install.sh --claude-code`）。
  2. `claude` 进入交互模式，输入 `/tr research "topic"`。
- OpenClaw 路径整理到 README 后段的 "Alternative runtimes" 小节。

### 8.5 `ARCHITECTURE.md`

- §2.x Platform adapters 列表中 `ClaudeCodeAdapter` 提升到首位。
- 图示（若有）里把 Claude Code agent 画在 orchestration 中心。
- 文末新增 "Claude Code integration reference"，指向 `docs/CLAUDE_CODE_ADAPTER.md`。

### 8.6 `ROADMAP.md`

- 勾选 "Source-level Claude Code integration"（原 v2 标注 "future direction"），改为 "shipped in v2.1"。
- 继续留 "Deeper MCP integration"、"Marketplace publish" 作为 v2.2 预告。

### 8.7 安装脚本默认分支

- 顶层 `install.sh`（phase 5 已是 dispatcher）：
  - 无 flag 进入交互菜单时，**默认高亮 "1) Claude Code"**（OpenClaw 仍列为选项 2，标 `legacy, still supported`）。
  - banner 文案改为 "Claude Code primary · OpenClaw legacy support"。
  - `runtimes/openclaw/install.sh` / `runtimes/claude-code/install.sh` **脚本本身不改**（职责不变，只是菜单层默认翻转）。
- `uninstall.sh`：同步文案。

### 8.8 版本号

- `pyproject.toml`：`version = "2.1.0"`。
- `runtimes/claude-code/plugin.json`：`version: "2.1.0"`（权威源）。
- `.claude-plugin/plugin.json` 作为软链自动跟进；若本地是拷贝则同步更新。
- `install.sh` header：`VERSION="2.1.0"`。

### 8.9 Release Notes

新增 `docs/release_notes/v2.1.0.md`（或 `CHANGELOG.md`，若仓库已有就追加）：

```markdown
# TrendR v2.1.0 — Claude Code-first release

## Highlights
- Claude Code becomes the primary runtime. OpenClaw remains supported.
- New `ClaudeCodeAdapter` with native + subprocess modes.
- 4 subagents (`paper-scout`, `paper-analyzer`, `review-lead`, `verifier`) and
  5 slash commands (`/tr research|hotspots|status|resume|template`).
- Plugin manifest at `.claude-plugin/plugin.json` for Claude Code plugin install.
- SessionStart / Stop / SubagentStop hooks for resumable runs.

## Breaking
- Runtime detection priority changed: `TRENDR_PLATFORM > CLAUDE_CODE_* > OPENCLAW_SESSION_ID > CODEX_* > cli`. If you rely on OpenClaw env alone, set `TRENDR_PLATFORM=openclaw` explicitly.

## Migration
- OpenClaw users: no changes required, behaviour unchanged.
- Claude Code users: `./install.sh --claude-code --user` or `claude /plugin install trendr` (when marketplace-enabled).
```

### 8.10 平台宣传资产（可选）

- 若仓库有 `assets/`（存在，已看到）：新增一张简图说明 Claude Code subagent 调度流程。
- 非必须，但建议。

## 步骤

1. 在 `main` 上建分支 `phase8/claude-code-primary`。
2. 按 8.1 → 8.9 顺序改动（8.10 可选）。
3. 执行 `python -m pytest tests/ -q`；若有 snapshot 断言被打破（CLI help snapshot），更新 snapshot 并确认符合预期。
4. 跑一次 `python cli.py run --help`、`python cli.py resume --help`、`python cli.py hotspots --help` 冒烟；确认文案正确。
5. 更新 `plan/STATUS.md`：phase 8 勾选；整张表全部变绿，"遗留 TODO"清理干净或转到 roadmap。
6. 写 PR / tag：`v2.1.0`。

## 验收

- [ ] `engine/runtime.py::detect_runtime({"CLAUDE_CODE_SESSION":"x"})` 返回 `"claude-code"`。
- [ ] `engine/runtime.py::detect_runtime({"OPENCLAW_SESSION_ID":"x"})` 仍返回 `"openclaw"`（OpenClaw 兼容不丢）。
- [ ] `python cli.py run --help` 默认示例显示 `--platform claude-code`。
- [ ] README 顶部第一屏呈现 Claude Code 安装流程。
- [ ] `pyproject.toml` / `plugin.json` / `install.sh` 版本全为 `2.1.0`。
- [ ] 全部测试通过：`python -m pytest tests/ -q`。
- [ ] `plan/STATUS.md` 所有 phase 均 "已完成"。

## 风险

- R-1（优先级改动破坏现有 OpenClaw 自动化）：用户若同时设置了 `CLAUDE_CODE_*` 和 `OPENCLAW_SESSION_ID`，新逻辑会选 Claude Code；release notes 已提示显式 `TRENDR_PLATFORM=openclaw` 的 override 方式。
- R-2（README 改写过大引起合并冲突）：phase 8 开始前，先 `git pull --rebase`；分支独立，尽量快速合入。
- R-3（版本跳号）：若 phase 7 已把版本推到 2.0.x，phase 8 只做 2.1.0；保证 semver 单调。
- 回滚：`git revert <phase8 commit>` 能单独回滚优先级改动；文档回滚会带回旧文案，可通过下一个 commit 微调。

## 后续（非 phase 8 范围）

- marketplace 发布（Anthropic 官方流程）。
- MCP 深度整合（chrome / linear / zotero）。
- OpenClaw 分支长期 LTS 策略：是否只做安全修复、版本冻结在 v2.0.x。
- agent rules 归一（从 phase 3 遗留的 "SOUL.md ↔ .claude/agents" 冗余收敛成共享段）。
