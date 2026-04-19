---
runtime: codex
parent_skill: chrome-cdp-setup
allowed-tools:
  - exec_command
  - read_thread_terminal
  - web
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（Chrome 146+ 安全约束、CDP 架构、双实例配置）见同目录 `SKILL.md`。本文件只描述 Codex 下的配置路径。

## Codex 下的浏览器自动化方案

Codex 不直接提供 OpenClaw 的 `browser --profile cdp` 原语。推荐优先级：

1. `exec_command(cmd="bash scripts/start-chrome-cdp.sh")`
2. `exec_command(cmd=".venv/bin/python3 scripts/cdp_browse.py '<url>' '<js_expr>'")`
3. `web.open` / `web.search_query`（静态页面或搜索兜底）

## 启动检查

```text
exec_command(cmd="curl -fsS http://127.0.0.1:19222/json/version 2>/dev/null && echo ready || echo not-running")
```

## Codex 限制

- 不调用 `openclaw browser` CLI。
- 没有 CDP 时，`web` 只做搜索和静态页面核对，不做 DOM 执行。
