---
runtime: claude-code
parent_skill: trendr-watchdog
allowed-tools:
  - Read
  - Write
  - Bash
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md`（`supervisor.py` 注入模式）。
> Claude Code 下，watchdog 由三个 Claude Code hooks 驱动，无需 `supervisor.py`。本文件为占位说明。
> hooks 的完整实现见 phase 6 产出的 `runtimes/claude-code/hooks/`。

## Claude Code 下的 Watchdog 机制

OpenClaw 的 `supervisor.py` 通过 `openclaw agent --session-id` 向主会话注入恢复消息。  
Claude Code 没有等价的会话注入 API，改用三个 **Claude Code hooks** 实现相同效果：

| Hook | 触发时机 | 作用 |
|------|---------|------|
| `SessionStart` | 每次 `claude` 启动/恢复会话 | 扫描 `~/research/**/run_state.json`，找 pending 的 run，作为 `additionalContext` 提示用户 `/tr resume` |
| `Stop` | 主 agent 结束回合 | 写终态 `heartbeat.json`，供下次 resume 判断断点 |
| `SubagentStop` | 子 agent 结束 | 写 `claude_code_completions/<handle>.json`，解除 ClaudeCodeAdapter 的阻塞 |

## 手动触发 Watchdog 检查（Claude Code）

如需手动检查 pending runs（无需 hooks）：

```
Bash(command="ls ~/research/*/run_state.json 2>/dev/null | head -10")
```

读取特定 run 状态：
```
Read(file_path="~/research/[PROJECT]/run_state.json")
Read(file_path="~/research/[PROJECT]/heartbeat.json")
```

## 与 phase 6 的关系

- `runtimes/claude-code/hooks/session_start.py` → 实现 SessionStart hook 逻辑
- `runtimes/claude-code/hooks/stop_heartbeat.py` → 实现 Stop hook 逻辑
- `runtimes/claude-code/hooks/subagent_stop.py` → 实现 SubagentStop hook 逻辑
- `engine/recovery/claude_code_resume.py` → 共享工具，`check_pending_runs()` + `format_context()`

hooks 通过 `~/.claude/settings.json` 注册（由 `runtimes/claude-code/install.sh` 完成 merge）。

## OpenClaw `supervisor.py` 保留

`skills/trendr-watchdog/supervisor.py` 原地不动，只在 `openclaw` runtime 下激活。  
Claude Code runtime 下此文件休眠，不被引用。
