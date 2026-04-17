---
runtime: claude-code
parent_skill: paper-scout
allowed-tools:
  - WebFetch
  - WebSearch
  - Bash
  - Read
  - Write
  - Grep
  - Glob
  - Agent
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md` 的原生指令块。
> 共享知识（源清单、字段契约、评分规则、速率限制）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

在 Claude Code 中执行学术论文搜索任务时，遵循以下流程：

1. 使用 `Bash` 创建必要目录：
   ```
   Bash: mkdir -p ~/research/[PROJECT]/{papers,notes}
   ```
2. 按优先级遍历 9 个 API 源（详见 `SKILL.md` §搜索源总览）。
3. 每个源使用 `WebFetch` 发起 HTTP GET（URL 见 `SKILL.md`）。
4. 汇总结果，去重并评分，写入 `candidates.csv`。
5. 对高分候选论文执行深挖（`SKILL.md` §深挖流程）。

## 指令映射

| OpenClaw 原语 | Claude Code 等价 |
|--------------|----------------|
| `web_fetch: { url: "..." }` | `WebFetch(url="...", prompt="返回原始响应体")` |
| `exec: sleep 3` | `Bash(command="sleep 3")` |
| `exec: mkdir -p ...` | `Bash(command="mkdir -p ...")` |
| `exec: python3 - <<'PY' ... PY` | `Bash(command="python3 -c '...'")` 或内联 Python |
| `read: ~/research/...` | `Read(file_path="~/research/...")` |
| `write: ~/research/...` | `Write(file_path="~/research/...", content=...)` |
| `openclaw browser --browser-profile cdp open <url>` | MCP chrome server（若安装） |
| `openclaw browser --browser-profile cdp evaluate --fn '...'` | MCP chrome `evaluate` |

## 各 API 源 WebFetch 调用

**arXiv**（速率 3s/次）：
```
WebFetch(
  url="http://export.arxiv.org/api/query?search_query=all:[QUERY]&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending",
  prompt="提取论文 ID、标题、摘要、作者、发布日期"
)
```

**Semantic Scholar**：
```
WebFetch(
  url="https://api.semanticscholar.org/graph/v1/paper/search?query=[QUERY_URL_ENCODED]&limit=20&fields=paperId,title,authors,year,abstract,citationCount,externalIds,venue,openAccessPdf",
  prompt="提取论文列表，每篇包含 paperId、title、year、citationCount"
)
```

**OpenAlex**：
```
WebFetch(
  url="https://api.openalex.org/works?search=[QUERY_URL_ENCODED]&per_page=20&sort=relevance_score:desc&filter=from_publication_date:2024-01-01",
  prompt="提取论文列表，包含 id、title、publication_year、cited_by_count"
)
```

其余源（PubMed、CrossRef、DBLP、Europe PMC、bioRxiv）的 URL 模板见 `SKILL.md` §API 调用清单。在 Claude Code 中，将 `web_fetch: { url: "..." }` 替换为对应 `WebFetch` 调用即可，URL 完全相同。

> ⚠️ **Papers with Code 已迁移至 Hugging Face**：`paperswithcode.com/search?q=...` 会重定向至 `huggingface.co/papers?q=...`，原 CSS 选择器（`.paper-card` 等）已失效。使用下方 HF Papers 指令。

**Hugging Face Papers**（替代 PwC，JS 渲染，需 CDP 或 scripts/cdp_browse.py）：
```
# CDP / scripts/cdp_browse.py 方式
navigate → "https://huggingface.co/papers?q=[QUERY_URL_ENCODED]"
wait 5s
evaluate:
  Array.from(document.querySelectorAll('article')).slice(0, 20).map(a => ({
    title: a.querySelector('h3')?.innerText?.trim() || '',
    url:   a.querySelector('h3 a')?.href || '',
    arxiv_id: (a.querySelector('h3 a')?.href || '').split('/papers/').pop(),
    upvotes: a.querySelector('[class*="upvote"]')?.innerText?.trim() || '0'
  })).filter(p => p.title.length > 5)
```

## CDP 浏览器采集（脚本路径 & Python 版本）

若项目中启动了 Chrome CDP（`bash scripts/start-chrome-cdp.sh`），可通过 `scripts/cdp_browse.py` 驱动浏览器采集 JS-heavy 学术页面：

```bash
Bash(command="bash scripts/start-chrome-cdp.sh")   # 确保 CDP 运行中
Bash(command=".venv/bin/python3 scripts/cdp_browse.py '<url>' '<js_expr>'")
```

**Python 版本规则**（避免 ModuleNotFoundError: websocket）：
- ✅ 使用 `.venv/bin/python3`（项目 venv，已安装 websocket-client）
- ✅ 使用 `/usr/bin/python3`（macOS 系统 Python 3.9，已有 websocket-client）
- ❌ 不用裸 `python3`（Homebrew 3.12，无 websocket-client）

## 浏览器兜底链（JS-heavy 内容）

优先级：
1. **scripts/cdp_browse.py**（CDP 已启动时）：完整 JS 渲染 + 真实 Cookie
2. **MCP chrome server**（若安装）：`mcp__chrome__navigate` + `mcp__chrome__evaluate`
3. **WebSearch**（降级）：`WebSearch(query="site:arxiv.org [QUERY] 2024..2025")`
4. **标记跳过**：`skipped_with_reason: "JS rendering required, no CDP or MCP available"`

## Claude Code 限制

- **arXiv 速率限制**：先访问 API 端点再访问网页会触发同 IP 限速；Depth A 任务优先用网页端（CDP 或 WebFetch），不用 API。
- **速率限制仍适用**：arXiv 3s/次、Semantic Scholar 无 key 时 30s/次；使用 `Bash(command="sleep N")` 遵守。
- **文件写入**：`Write` 工具创建父目录，不需要额外 `mkdir`；大文件分块写入避免截断。
