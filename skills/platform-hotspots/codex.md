---
runtime: codex
parent_skill: platform-hotspots
allowed-tools:
  - exec_command
  - web
  - spawn_agent
  - wait_agent
  - send_input
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（平台列表、输出格式、聚合规则）见同目录 `SKILL.md`。本文件只描述 Codex 工具调用方式。

## 使用方法

对每个平台按以下优先级链执行抓取，并聚合写入输出文件。

## 工具优先级链

```text
1. Chrome CDP 脚本
   exec_command(cmd="bash scripts/start-chrome-cdp.sh")
   exec_command(cmd=".venv/bin/python3 scripts/cdp_browse.py '<url>' '<js_expr>'")
2. web.open / web.search_query
3. exec_command + curl（静态页面 / JSON API）
4. skipped_with_reason
```

## 各平台 Codex 抓取方式

### GitHub Trending
```text
web.open(ref_id="https://github.com/trending")
```
或
```text
exec_command(cmd='curl -fsSL "https://github.com/trending?since=daily&spoken_language_code="')
```

### Hacker News
```text
exec_command(cmd='curl -fsSL "https://news.ycombinator.com/"')
```

### Reddit
```text
exec_command(cmd='curl -fsSL "https://www.reddit.com/r/MachineLearning/hot.json?limit=20"')
```

### GitHub / HN / Product Hunt 以外的 JS-heavy 平台
优先走 `scripts/cdp_browse.py`；无 CDP 时再用：
```text
web.search_query(q="[platform] AI 热点 today")
```

### Hugging Face Papers
`paperswithcode.com/search` 已迁移，Codex 下同样优先抓 `https://huggingface.co/papers?q=[QUERY]`。

## 输出文件

- `hotspots_report.md`
- `hotspots_summary.md`

即使部分平台被标记 `skipped_with_reason`，也必须生成输出文件。

## Codex 限制

- `web` 工具不能替代真实浏览器执行；JS-heavy 平台优先走 CDP 脚本。
- 默认顺序抓取；只有平台切片完全独立且宿主允许委派时，才用 `spawn_agent`。
