# Phase 6 — Hooks（`runtimes/claude-code/hooks/`）+ Watchdog 路径分离

> 遵循 [`plan/structure.md`](./structure.md) §1 / §2。
> 产出：
> - `runtimes/claude-code/hooks/` 下 3 个 Python hook 脚本
> - `runtimes/claude-code/settings.json.example`
> - `engine/recovery/claude_code_resume.py`（共享 utility）
> - `skills/trendr-watchdog/claude-code.md` 用 Claude Code 语义描述 watchdog（phase 2 已创占位）
> 目标：Claude Code 下的 heartbeat / resume / watchdog 行为由 Claude Code hooks 驱动；OpenClaw 的 `supervisor.py` 保留在原地不改，两边互不干扰。
> 依赖 phase：1（ClaudeCodeAdapter dispatch/completion 协议）；3 / 5（manifest 引用 hooks）。

## 三类 hook 职责

| Hook | 触发时机 | 本 phase 脚本做的事 |
|------|---------|-------------------|
| `SessionStart` | 每次 `claude` 启动/恢复会话 | 扫描 `~/research/**/run_state.json`，找 `status in {running, paused, failed}` 的 run，把摘要作为 `additionalContext` 返回给 Claude |
| `Stop` | 主 agent 结束回合 | 若当前有 TrendR project_dir，写终态 heartbeat.json，便于下次 resume |
| `SubagentStop` | 子 agent 结束 | 若 subagent 是 TrendR 四家之一，把最终 output 写 `claude_code_completions/<handle>.json`，解除状态机阻塞 |

## 文件规范

### 6.1 `runtimes/claude-code/hooks/session_start.py`

- Shebang `#!/usr/bin/env python3`
- 只用标准库（`json`, `os`, `sys`, `pathlib`, `datetime`, `subprocess`）
- 读 stdin payload（Claude Code hook 协议；解析失败静默退出 0）
- 调用 `engine.recovery.claude_code_resume.check_pending_runs`
- 输出：
  ```json
  {
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": "TrendR: 2 run(s) pending. Latest: ~/research/rl-mm (state=ANALYSIS, updated 12m ago). Run `/tr resume <dir>` to continue."
    }
  }
  ```
- 执行时间 < 2 秒

### 6.2 `runtimes/claude-code/hooks/stop_heartbeat.py`

- 读 stdin payload `{ transcript_path, stop_hook_active, ... }`
- 若 `stop_hook_active == true`：直接退出 0（避免递归）
- 探测当前 TrendR project_dir：按以下顺序
  1. env `TRENDR_PROJECT_DIR`
  2. `~/research/*/run_state.json` 最近 5 分钟内 mtime 变化过的
- 若找到：写 `<project_dir>/heartbeat.json`：
  ```json
  {
    "agent": "claude-code-session",
    "state": "<current_state from run_state.json>",
    "message": "claude stopped",
    "updated_at": "<ISO>",
    "stopped_at": "<ISO>"
  }
  ```
- 写入使用 `os.replace(tmp, target)` 原子替换

### 6.3 `runtimes/claude-code/hooks/subagent_stop.py`

- 读 stdin payload：`{ subagent_type, final_message, transcript_path, ... }`
- 若 `subagent_type` 不在 `{paper-scout, paper-analyzer, review-lead, verifier}`：退出 0
- 探测 project_dir（同 6.2）
- 找到 pending completion：`<project_dir>/claude_code_dispatch.jsonl` 里找未被完成的、`agent_id == subagent_type` 的最早一条
- 写 `<project_dir>/claude_code_completions/<handle>.json`：
  ```json
  {
    "handle": "<h>",
    "status": "completed",
    "output": "<final_message>",
    "artifacts": [],
    "ended_at": "<ISO>"
  }
  ```

### 6.4 通用规则

每个 hook 脚本都：
- 在顶部 `try: ... except Exception: sys.exit(0)` 兜底，绝不阻塞 Claude Code 启动
- 写一行日志到 `~/.trendr/hooks.log`（格式：`<ISO> <event> <summary>`）
- `chmod +x`
- **只依赖标准库**（方便 `python` 直接跑，不需 pip install）

### 6.5 `engine/recovery/claude_code_resume.py`（共享 utility）

```python
from pathlib import Path
from typing import Iterable

def check_pending_runs(root: Path = Path.home()/"research", limit: int = 5) -> list[dict]:
    """Return pending runs (status running/paused/failed), newest first."""
    ...

def format_context(runs: Iterable[dict]) -> str:
    """One-line-per-run context string for SessionStart additionalContext."""
    ...
```

被 `hooks/session_start.py` 与 `cli.py::cmd_status` 共用。所在包 `engine/recovery/` 已存在（见 `engine/recovery/heartbeat.py` 等），直接加新文件即可。

### 6.6 `runtimes/claude-code/settings.json.example`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "python \"${CLAUDE_PLUGIN_ROOT:-$(pwd)}/runtimes/claude-code/hooks/session_start.py\"" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python \"${CLAUDE_PLUGIN_ROOT:-$(pwd)}/runtimes/claude-code/hooks/stop_heartbeat.py\"" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "python \"${CLAUDE_PLUGIN_ROOT:-$(pwd)}/runtimes/claude-code/hooks/subagent_stop.py\"" }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Read",
      "Write",
      "WebFetch",
      "WebSearch",
      "Agent"
    ]
  }
}
```

注意：这是**示例**，用户通过 phase 5 installer 把内容 merge 进 `~/.claude/settings.json`，而不是直接拷贝覆盖。

## 与 phase 1 ClaudeCodeAdapter 的接口

- adapter `native` 模式：`spawn_agent` 写 dispatch 行，`await_agent` 轮询 completion 文件。
- subagent 跑完 → Claude Code 触发 `SubagentStop` → hook 写 completion → adapter 解除阻塞。
- 会话中途被关 → `Stop` hook 写终态 heartbeat → 下次 `SessionStart` 扫描到 pending run → 提醒用户 `/tr resume`。

## OpenClaw Watchdog 保留

- `skills/trendr-watchdog/supervisor.py` 原地不动。
- `skills/trendr-watchdog/SKILL.md` 的 Runtime Router（phase 2 改过）指：
  - `openclaw` → 用 `supervisor.py`
  - `claude-code` → 看 `skills/trendr-watchdog/claude-code.md`
- 本 phase 更新 `skills/trendr-watchdog/claude-code.md` 正文：描述三个 hook 的角色、用户开关方式、与 phase 5 installer 的 settings merge 关系。

## 步骤

1. 新建 `runtimes/claude-code/hooks/` 目录，放入 3 个 Python 脚本 + `README.md`（职责说明）。
2. 每个脚本按 6.1-6.3 实现；`chmod +x`；只用标准库。
3. 新建 `engine/recovery/claude_code_resume.py`。
4. 新建 `runtimes/claude-code/settings.json.example`（按 6.6）。
5. 更新 `skills/trendr-watchdog/claude-code.md` 正文（phase 2 已创占位文件）。
6. 在 `engine/watchdog.py` 加一行启动时检查：若环境有 `CLAUDE_CODE_*` 且 hook 脚本存在，打印 INFO "hooks detected, watchdog will run in passive mode" 并减少轮询频率（不关，但不抢 hook 的活）。
7. 新建 `tests/test_hooks.py`：
   - 每个 hook 的 stdin → stdout 契约
   - `SessionStart` 无 pending / 有 pending 两种分支
   - `Stop` 在 `stop_hook_active` 时退出 0 不写文件
   - `SubagentStop` 写 completion 的路径 / 内容
   - 用 tmp_path 隔离
8. 冒烟：`python runtimes/claude-code/hooks/session_start.py < /dev/null` 退出码 0，输出 JSON 合法。
9. 更新 `plan/STATUS.md` phase 6。

## 验收

- [ ] `runtimes/claude-code/hooks/` 下 3 个脚本可执行、只依赖标准库。
- [ ] `engine/recovery/claude_code_resume.py` 提供 `check_pending_runs` + `format_context`。
- [ ] `python -m pytest tests/test_hooks.py -q` 通过。
- [ ] `runtimes/claude-code/settings.json.example` JSON 合法；phase 5 installer 会 merge 它。
- [ ] `skills/trendr-watchdog/claude-code.md` 含 Claude Code 下 watchdog 行为描述。
- [ ] OpenClaw 的 `skills/trendr-watchdog/supervisor.py` 未修改。
- [ ] `plan/STATUS.md` phase 6 勾选。

## 风险

- R-1（hook 报错阻塞会话启动）：try/except 兜底 + 静默退出 0。
- R-2（并发写 heartbeat.json）：原子替换；多个 hook 不会同时写同一个 run（SessionStart 只读，Stop 只写当前 run）。
- R-3（SubagentStop 无法匹配 handle）：fallback 写一个 "auto-detected" 的 completion，带 `status=completed` 与原始 `final_message`；状态机会继续推进，若结果不对下一轮 validator 会捕获。
- R-4（`CLAUDE_PLUGIN_ROOT` 未设置）：settings.json.example 用 `${CLAUDE_PLUGIN_ROOT:-$(pwd)}` fallback；dev 环境指向当前目录。
- 回滚：`git revert` + 删 `runtimes/claude-code/hooks/` + 删 `runtimes/claude-code/settings.json.example` + 删 `engine/recovery/claude_code_resume.py`。

## 不做的事

- 不动 OpenClaw `supervisor.py`。
- 不改 runtime 优先级（phase 8）。
- 不改 slash commands（phase 4 定型）。
