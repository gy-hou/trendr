---
runtime: claude-code
parent_skill: platform-hotspots
allowed-tools:
  - WebFetch
  - WebSearch
  - Bash
  - Read
  - Write
  - Agent
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md`（`openclaw browser --browser-profile cdp` 模式）。
> 共享知识（平台列表、输出格式、聚合规则）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

对每个平台按以下优先级链执行抓取，将结果聚合写入输出文件。

## 工具优先级链（适用所有平台）

```
1. MCP chrome server（若安装）
   mcp__chrome__navigate(url=...) → mcp__chrome__evaluate(script=...)
2. WebFetch（静态页面 / API 端点）
   WebFetch(url=..., prompt="提取热点列表")
3. WebSearch（JS-heavy 且无 MCP chrome）
   WebSearch(query="site:[platform.com] 热点 2024")
4. 跳过并标注
   skipped_with_reason: "JS rendering required, no MCP chrome or WebSearch available"
```

## 各平台 Claude Code 抓取方式

### GitHub Trending（静态，WebFetch 即可）
```
WebFetch(
  url="https://github.com/trending?since=daily&spoken_language_code=",
  prompt="提取前 20 个 trending repo：名称、语言、stars、描述"
)
```

### Hacker News（静态，WebFetch 即可）
```
WebFetch(
  url="https://news.ycombinator.com/",
  prompt="提取前 30 条帖子：标题、URL、分数、评论数"
)
```

### Product Hunt（静态 API 端点）
```
WebFetch(
  url="https://www.producthunt.com/",
  prompt="提取今日热门产品：名称、tagline、投票数"
)
```

### Hugging Face Papers（替代 PwC，JS-heavy）
> ⚠️ `paperswithcode.com/search` 已重定向至 HF Papers，原 `.paper-card` 选择器失效。
```
# CDP / scripts/cdp_browse.py（优先）
navigate → "https://huggingface.co/papers?q=[QUERY]"
wait 5s
evaluate:
  Array.from(document.querySelectorAll('article')).slice(0,20).map(a=>({
    title: a.querySelector('h3')?.innerText?.trim()||'',
    arxiv_id: (a.querySelector('h3 a')?.href||'').split('/papers/').pop(),
    upvotes: a.querySelector('[class*="upvote"]')?.innerText?.trim()||'0'
  })).filter(p=>p.title.length>5)

# WebSearch（降级）
WebSearch(query="site:huggingface.co/papers [QUERY] 2024 2025")
```

### 知乎热榜（JS-heavy）
优先 MCP chrome，降级用 WebSearch：
```
# MCP chrome（优先）
mcp__chrome__navigate(url="https://www.zhihu.com/hot")
mcp__chrome__evaluate(script="() => Array.from(document.querySelectorAll('.HotItem')).map(e => ({title: e.querySelector('.HotItem-title')?.textContent?.trim(), heat: e.querySelector('.HotItem-metrics')?.textContent?.trim()}))")

# WebSearch（降级）
WebSearch(query="知乎热榜 今日热点 AI 科技 site:zhihu.com")
```

### X/Twitter（JS-heavy）
```
# MCP chrome（优先）
mcp__chrome__navigate(url="https://x.com/search?q=(AI OR agent OR LLM)&f=live")
mcp__chrome__evaluate(script="() => Array.from(document.querySelectorAll('[data-testid=tweet]')).slice(0,20).map(e => e.textContent.trim())")

# WebSearch（降级）
WebSearch(query="X Twitter AI agent LLM trending today 2025")
```

### Reddit（静态 JSON API 可用）
```
WebFetch(
  url="https://www.reddit.com/r/MachineLearning/hot.json?limit=20",
  prompt="提取前 20 帖子：标题、分数、评论数、URL"
)
```

### 小红书（JS-heavy）
```
# MCP chrome（优先）
mcp__chrome__navigate(url="https://www.xiaohongshu.com/explore")
mcp__chrome__evaluate(script="() => Array.from(document.querySelectorAll('.note-item')).slice(0,20).map(e => e.textContent.trim())")

# WebSearch（降级）
WebSearch(query="小红书 科技 AI 热点 今日")
```

### YouTube Trending（JS-heavy）
```
# MCP chrome（优先）
mcp__chrome__navigate(url="https://www.youtube.com/feed/trending")
mcp__chrome__evaluate(script="() => Array.from(document.querySelectorAll('#video-title')).slice(0,20).map(e => e.textContent.trim())")

# WebSearch（降级）
WebSearch(query="YouTube trending AI technology today")
```

## 输出文件

```
Write(file_path="~/research/[PROJECT]/hotspots_report.md", content=...)
Write(file_path="~/research/[PROJECT]/hotspots_summary.md", content=...)  # 摘要版
```

输出字段格式见 `SKILL.md` §输出格式。

## 兜底链总结

- 所有 9 个平台抓取完成后，即使部分平台被标记 `skipped_with_reason`，也应生成输出文件。
- 至少 4 个平台成功抓取时，视为 `status: partial_success`。
- 少于 4 个时，`status: degraded`，在输出文件中注明原因。

## Claude Code 限制

- 不能调用 `openclaw browser` CLI；MCP chrome server 是唯一支持 JS 渲染的方式。
- 若未安装 MCP chrome server，静态页面（GitHub、HN、Reddit JSON API）仍可抓取。
- `WebSearch` 结果非实时，可能有延迟；标注 `source: websearch` 以示区分。
