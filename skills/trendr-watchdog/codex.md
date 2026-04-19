---
runtime: codex
parent_skill: trendr-watchdog
allowed-tools:
  - exec_command
  - read_thread_terminal
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> Codex 下不使用 `supervisor.py` 会话注入；采用文件型 heartbeat / resume 协议。

## Codex 下的 Watchdog 机制

Codex 与 CLI runtime 共享同一条恢复路径：

1. 用 `engine/watchdog.py` 监控 `heartbeat.json` 与 `run_state.json`
2. 发现卡死或超时后，写 `resume_request.json`
3. 由状态机循环消费恢复请求，而不是向宿主会话注入消息

## 手动检查

```text
exec_command(cmd="ls ~/research/*/run_state.json 2>/dev/null | head -10")
exec_command(cmd="sed -n '1,200p' ~/research/[PROJECT]/run_state.json")
exec_command(cmd="sed -n '1,200p' ~/research/[PROJECT]/heartbeat.json")
```

启动 watchdog：

```text
exec_command(cmd='PROJECT="[project]" && nohup python3 engine/watchdog.py ~/research/"$PROJECT" >> ~/research/"$PROJECT"/logs/watchdog.out 2>&1 & echo $! > ~/research/"$PROJECT"/logs/watchdog.pid')
```

## Codex 限制

- 不做会话注入，不依赖 hooks。
- 终态必须写回 `heartbeat.json`，否则下次 resume 会误判为未完成。
