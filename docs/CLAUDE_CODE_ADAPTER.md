# ClaudeCodeAdapter — Dispatch Protocol & Mode Reference

## Overview

`ClaudeCodeAdapter` bridges the TrendR v2 state machine with Claude Code as the host runtime. It supports two operating modes:

| Mode | When used | Description |
|------|-----------|-------------|
| `native` | Inside a Claude Code session | Writes dispatch requests to `claude_code_dispatch.jsonl`; polls `claude_code_completions/<handle>.json` |
| `subprocess` | Outside Claude Code | Delegates to `CLIAdapter`, which calls `claude -p` via subprocess |

## Mode Selection

The mode is selected when `get_adapter("claude-code")` is called in `cli.py`:

1. If `TRENDR_CC_MODE=native` or `TRENDR_CC_MODE=subprocess` is set, use it explicitly.
2. Otherwise: if any `CLAUDE_CODE_*` env variable is present → `native`; else → `subprocess`.

You can also force the mode by setting `TRENDR_CC_MODE` in your shell before running the CLI.

## Native Mode — Dispatch File Format

### `<project_dir>/claude_code_dispatch.jsonl`

Append-only JSON Lines file. Each line is one pending operation for the host Claude Code agent.

**Agent dispatch:**
```json
{
  "handle": "paper-scout_1713350400123",
  "op": "agent",
  "agent_id": "paper-scout",
  "subagent_type": "paper-scout",
  "task": "Search for papers on ...",
  "timeout_sec": 900,
  "created_at": "2026-04-17T13:00:00Z"
}
```

**HTTP fetch:**
```json
{
  "handle": "webfetch_1713350400456",
  "op": "webfetch",
  "url": "https://api.semanticscholar.org/...",
  "headers": {},
  "created_at": "2026-04-17T13:00:01Z"
}
```

**Shell command:**
```json
{
  "handle": "bash_1713350400789",
  "op": "bash",
  "command": "mkdir -p ~/research/my-project/notes",
  "timeout_sec": 30,
  "created_at": "2026-04-17T13:00:02Z"
}
```

**Browser eval:**
```json
{
  "handle": "browser_1713350400999",
  "op": "browser_eval",
  "tool": "mcp__chrome__evaluate",
  "url": "https://zhihu.com/hot",
  "js": "() => Array.from(document.querySelectorAll('.hot-list-item')).map(e => e.textContent.trim())",
  "created_at": "2026-04-17T13:00:03Z"
}
```

### `<project_dir>/claude_code_completions/<handle>.json`

Written by the host Claude Code agent (or by hooks in phase 6) to signal completion:

```json
{
  "handle": "paper-scout_1713350400123",
  "status": "completed",
  "output": "Found 35 candidates, wrote candidates.csv",
  "artifacts": ["candidates.csv", "search_log.md"],
  "error": null,
  "ended_at": "2026-04-17T13:22:00Z"
}
```

`status` values: `completed` | `failed` | `timeout`

## Lifecycle

1. `adapter.init_run()` — rotate any stale dispatch file from a previous run.
2. State machine calls `adapter.spawn_agent(agent_id, task)` → adapter writes a dispatch line, returns a `handle`.
3. State machine calls `adapter.await_agent(handle)` → adapter polls the completion file (every `poll_sec` seconds, up to `max_wait_sec`).
4. If the completion file appears, return its contents. If timeout is reached, return `{"status": "timeout"}`.

## Phase 6 Integration

Phase 6 adds three Claude Code hooks that automatically write completion files:

- `SubagentStop` hook → writes `claude_code_completions/<handle>.json` when a subagent finishes.
- `Stop` hook → writes terminal `heartbeat.json` for resumability.
- `SessionStart` hook → scans for pending runs and adds context to the next session.

Until phase 6 is complete, the host Claude Code agent must manually satisfy dispatch ops (e.g., via the `/tr research` slash command in phase 4).
