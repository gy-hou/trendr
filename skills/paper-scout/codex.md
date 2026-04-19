---
runtime: codex
parent_skill: paper-scout
allowed-tools:
  - exec_command
  - web
  - spawn_agent
  - wait_agent
  - send_input
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（源清单、字段契约、评分规则、速率限制）见同目录 `SKILL.md`。本文件只描述 Codex 工具调用方式。

## 使用方法

在 Codex 中执行学术论文搜索任务时，默认顺序执行：

1. 用 `exec_command` 创建目录：
   ```text
   exec_command(cmd="mkdir -p ~/research/[PROJECT]/{papers,notes}")
   ```
2. 按 `SKILL.md` §搜索执行策略 选择 3-5 个 API 源。
3. 精确 API 调用优先用 `exec_command` + `curl`；站点级补检索用 `web.search_query` / `web.open`。
4. 汇总结果、去重并评分，写入 `candidates.csv` 与 `search_log.md`。
5. 只有在宿主请求明确允许委派，或当前 run 已经处于多 agent 调度流中时，才使用 `spawn_agent` 并行拆分查询。

## 指令映射

| OpenClaw 原语 | Codex 等价 |
|--------------|-----------|
| `web_fetch: { url: "..." }` | `exec_command(cmd='curl -fsSL \"...\"')`；需要快速页面级检查时用 `web.open` |
| `web_search <query>` | `web.search_query(q=\"...\")` |
| `exec: sleep 3` | `exec_command(cmd=\"sleep 3\")` |
| `exec: mkdir -p ...` | `exec_command(cmd=\"mkdir -p ...\")` |
| `read: ~/research/...` | `exec_command(cmd=\"sed -n '1,200p' ...\")`、`rg`、或现有脚本 |
| `write: ~/research/...` | 优先调用仓库已有脚本；必要时用 `exec_command` 执行原子写入 |
| `sessions_spawn` | 默认不用；明确允许并行时才用 `spawn_agent(...)` |
| `sessions_yield` | `wait_agent(...)` |
| `openclaw browser --browser-profile cdp ...` | `exec_command` + `scripts/start-chrome-cdp.sh` / `scripts/cdp_browse.py`；无 CDP 时降级到 `web.search_query` |

## 各 API 源调用

**arXiv**（速率 3s/次）：
```text
exec_command(cmd='curl -fsSL "http://export.arxiv.org/api/query?search_query=all:[QUERY]&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending"')
exec_command(cmd="sleep 3")
```

**Semantic Scholar**：
```text
exec_command(cmd='curl -fsSL "https://api.semanticscholar.org/graph/v1/paper/search?query=[QUERY_URL_ENCODED]&limit=20&fields=paperId,title,authors,year,abstract,citationCount,externalIds,venue,openAccessPdf"')
```

**OpenAlex**：
```text
exec_command(cmd='curl -fsSL "https://api.openalex.org/works?search=[QUERY_URL_ENCODED]&per_page=20&sort=relevance_score:desc&filter=from_publication_date:2024-01-01"')
```

其余源（PubMed、CrossRef、DBLP、Europe PMC、bioRxiv）的 URL 模板见 `SKILL.md` §API 调用清单。Codex 下直接复用这些 URL，不改字段契约。

## 浏览器兜底链

优先级：

1. `exec_command(cmd="bash scripts/start-chrome-cdp.sh")`
2. `exec_command(cmd=".venv/bin/python3 scripts/cdp_browse.py '<url>' '<js_expr>'")`
3. `web.search_query(q="site:arxiv.org [QUERY] 2024..2025")`
4. `skipped_with_reason`

Hugging Face Papers、Google Scholar、Semantic Scholar 网页版等 JS-heavy 页面，优先走 `scripts/cdp_browse.py`；不要把 `web.search_query` 当作实时页面执行器。

## Codex 限制

- Codex 的 `web` 工具适合搜索与静态页面核对，不替代 JS 执行环境。
- 写 `candidates.csv` / `search_log.md` 时保持文件落盘优先，不要只在上下文中汇总结果。
- 默认顺序执行；只有在 DISCOVERY 边界足够清晰且主请求允许时才并行拆分。
