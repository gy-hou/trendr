---
runtime: claude-code
parent_skill: chrome-cdp-setup
allowed-tools:
  - Bash
  - Read
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md`（OpenClaw 浏览器 profile 配置）。
> 共享知识（Chrome 146+ 安全约束、CDP 架构、双实例配置）见同目录 `SKILL.md`。本文件只描述 Claude Code 下的配置路径。

## Claude Code 下的浏览器自动化方案

Claude Code 不能直接调用 `openclaw browser --browser-profile cdp`。  
推荐按以下优先级使用浏览器能力：

### 方案 1：MCP chrome server（推荐）

如果项目中配置了 MCP chrome server（例如 `@anthropic/mcp-server-chrome`），可直接使用：

```
mcp__chrome__navigate(url="https://example.com")
mcp__chrome__evaluate(script="() => document.title")
mcp__chrome__screenshot()
```

安装 MCP chrome server：参考官方文档或 `~/.claude/settings.json` 中的 `mcpServers` 配置。

### 方案 2：WebFetch（静态页面）

对不需要 JavaScript 渲染的页面，直接用 `WebFetch`：

```
WebFetch(url="https://github.com/trending", prompt="提取 trending repos")
```

### 方案 3：手动 CDP（高级）

若需要复用 OpenClaw 的 CDP 启动脚本：

```
Bash(command="bash ~/Documents/GitHub/trendr/scripts/start-chrome-cdp.sh")
```

然后通过 `WebFetch` 调 CDP API（`http://127.0.0.1:19222/json`）或通过 Playwright/Puppeteer。

## Chrome CDP 启动检查

检查 CDP 是否已启动：
```
Bash(command="curl -fsS http://127.0.0.1:19222/json/version 2>/dev/null && echo 'CDP running' || echo 'CDP not running'")
```

## Claude Code 限制

- **不使用 `openclaw browser` CLI**：这是 OpenClaw 专属工具。
- MCP chrome server 是在 Claude Code 中获得 CDP 等价能力的唯一官方路径。
- 若无 MCP chrome，`WebFetch` 覆盖大多数静态内容场景（GitHub、HN、Reddit JSON API）。
