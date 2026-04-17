---
name: paper-scout
description: 9 源学术论文搜索与筛选（arXiv, Semantic Scholar, OpenAlex, PubMed, CrossRef, DBLP, Europe PMC, bioRxiv, Papers with Code），利用本机已安装工具，零额外依赖
metadata: {"openclaw": {}}
---

# Paper Scout Skill

9 源学术论文发现与筛选。所有 API 均为公开免费，直接通过 HTTP GET 调用，无需安装任何额外 MCP server。

> ⚠️ 每次执行搜索任务前，完整阅读本文件。不要跳过任何部分。

## Runtime Router (Mandatory)

在执行任何命令前，先确定当前 runtime，并只执行对应命令块：

1. 运行时识别优先级：`TRENDR_PLATFORM` > `OPENCLAW_SESSION_ID` > `CODEX_*` > `CLAUDE_CODE_*` > `cli`
2. canonical runtime：`openclaw`、`codex`、`claude-code`、`cli`
3. 别名归一：`claudecode -> claude-code`
4. 仅执行命中 runtime 的步骤；其余 runtime 步骤必须标记为 `dormant` 并显式跳过

## Multi-Platform Compatibility

This skill uses `web_fetch:` syntax (OpenClaw native). On other platforms:
- **Claude Code**: Use `WebFetch` tool or `curl` via Bash. The URL in `web_fetch: { url: "..." }` is a standard HTTP GET.
- **Codex**: Use `fetch()`, `curl`, or `requests.get()`. Same URLs apply.
- **`exec:`** commands: Use your shell execution tool (Bash, terminal, etc.)
- All API URLs are plain REST endpoints — copy the URL and call with any HTTP client.

## 搜索源总览

| # | 源 | 覆盖范围 | 速率限制 | 需要 Key |
|---|------|---------|---------|---------|
| 1 | arXiv | CS/数学/物理预印本 | 3秒/次 | 否 |
| 2 | Semantic Scholar | 2亿+ 论文，引用网络 | 100次/5分钟(有key) | 推荐 |
| 3 | OpenAlex | 2.5亿+ 作品，全开放 | 无限制(有email更快) | 否 |
| 4 | PubMed | 生物医学 3600万+ | 3次/秒(有key) | 否 |
| 5 | CrossRef | DOI 注册论文 1.4亿+ | 友好限制 | 否 |
| 6 | DBLP | 计算机科学文献库 | 宽松 | 否 |
| 7 | Europe PMC | 欧洲生命科学 4000万+ | 宽松 | 否 |
| 8 | bioRxiv | 生物学预印本 | 宽松 | 否 |
| 9 | Papers with Code | 带代码的 ML 论文 | 宽松 | 否 |

## 搜索执行策略

**不要一次性调用 9 个源。** 按研究领域选择最相关的 3-5 个源：

- **CS / AI / ML 方向** → arXiv + Semantic Scholar + OpenAlex + DBLP + Papers with Code
- **生物医学方向** → PubMed + Europe PMC + bioRxiv + Semantic Scholar + OpenAlex
- **通用/跨学科** → Semantic Scholar + OpenAlex + CrossRef + arXiv

每个源之间等待 2-3 秒避免速率限制。

## 稳定性与兜底（必须执行）

如果出现以下任一情况，不得直接结束任务，必须进入兜底检索：

- `web_fetch` 返回：`Blocked: resolves to private/internal/special-use IP address`
- 连续 2 个数据源出现 429 / 5xx / 空响应
- 单轮搜索 120 秒无新增候选论文

兜底检索顺序（按优先级）：

1. `arxiv-watcher`（优先拿可用论文元数据）
2. Chrome CDP 浏览器搜索（Google Scholar / Semantic Scholar 网页版）
3. `tavily-search`（跨站点学术检索）
4. `web_search`（补齐来源覆盖）

兜底查询模板：

```text
academic paper [QUERY] site:arxiv.org OR site:semanticscholar.org OR site:openalex.org
```

进入兜底后仍要继续评分、去重，并输出标准 `candidates.csv`。

### Chrome CDP 浏览器兜底

前置条件：
1. 检查 Chrome CDP 是否已启动：`exec: curl -fsS http://127.0.0.1:19222/json/version`
2. 如果未启动，先执行：`exec: bash scripts/start-chrome-cdp.sh` 或 `exec: bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh`
   - 现有本地用户默认继续复用 legacy `19222 + cdp-automation`
   - 新用户/新会话建议先用：`exec: TRENDR_CDP_USER=<user-key> bash scripts/start-chrome-cdp.sh`
3. 确认返回 `ready:19222` 后再继续
4. 浏览器兜底只用于临时提取结果，不保留学术站页面；抓取完成后必须关闭当前 tab
5. 所有浏览器调用都必须显式带 `profile: cdp`；不允许空 profile 调用
6. 如果需要登录 Google Scholar / X / arXiv 等站点，提醒用户在 dedicated agent Chrome 里先登录一次，后续运行复用同一套 CDP store

用 browser 工具搜索（profile 必须是 `cdp`，不是旧 profile）：

```bash
browser --profile cdp navigate "https://scholar.google.com/scholar?q=multi-agent+reinforcement+learning+2025"
browser --profile cdp eval "Array.from(document.querySelectorAll('.gs_ri')).slice(0,20).map(e => ({title: e.querySelector('.gs_rt')?.textContent, url: e.querySelector('.gs_rt a')?.href, snippet: e.querySelector('.gs_rs')?.textContent, cite: e.querySelector('.gs_fl a')?.textContent})).filter(e => e.title)"
```

Semantic Scholar 网页版兜底：

```bash
browser --profile cdp navigate "https://www.semanticscholar.org/search?q=multi-agent+systems&year%5B0%5D=2024&year%5B1%5D=2025"
browser --profile cdp eval "Array.from(document.querySelectorAll('[data-test-id=\"result\"]')).slice(0,20).map(e => ({title: e.querySelector('.cl-paper-title')?.textContent, url: e.querySelector('.cl-paper-title a')?.href, year: e.querySelector('.cl-paper-pubdate')?.textContent, cite_count: e.querySelector('.cl-paper-stats')?.textContent})).filter(e => e.title)"
```

OpenClaw 原生命令下，优先用 `open/evaluate/close` 模式，不要长期停留在搜索结果页：

```bash
OPEN_OUT=$(openclaw browser --browser-profile cdp open "https://arxiv.org/search/?query=multi-agent+systems&searchtype=all")
TAB_ID=$(printf '%s\n' "$OPEN_OUT" | awk '/^id:/{print $2}' | tail -n1)
openclaw browser --browser-profile cdp evaluate --fn '() => Array.from(document.querySelectorAll(\"li.arxiv-result\")).slice(0, 20).map(e => ({title: e.querySelector(\"p.title\")?.textContent?.trim(), url: e.querySelector(\"p.list-title a\")?.href, abstract: e.querySelector(\"span.abstract-full\")?.textContent?.trim()})).filter(e => e.title)'
openclaw browser --browser-profile cdp close "$TAB_ID"
```

执行约束：
- 一次只开一个学术搜索 tab
- 提取完成立即 `close "$TAB_ID"`；不要把 arXiv / Google Scholar / Semantic Scholar 页面留在前台
- 如果需要切换下一个站点，重新 `open` 新 tab，不复用旧 tab
- 若遇到 `selected page has been closed`，重新 `open` 当前 URL，不要继续复用失效 tab

## 深挖模式（Scrapling）

当任务包含以下任一关键词时，必须开启深挖模式：
- `深入爬取`
- `深挖`
- `深度研究`
- `deep crawl`

### 深挖模式强制步骤

1. 先完成常规 3-5 源 API 搜索和去重，生成 `candidates.csv`
2. 从 `candidates.csv` 中选 `relevance_score >= 4` 的前 10 篇（不足则全选）
3. 对每篇构造落地页 URL，优先级：
   - `source=arxiv` 且 `paper_id` 为 arXiv ID → `https://arxiv.org/abs/[paper_id]`
   - `paper_id` 是 DOI（`10.` 开头） → `https://doi.org/[paper_id]`
   - 其他 → 用标题构造 Semantic Scholar 搜索 URL
4. 用 Scrapling 抓取页面正文片段，输出：
   - `~/research/[PROJECT]/scrapling_extracts.jsonl`
   - `~/research/[PROJECT]/crawl_log.md`

### Scrapling 执行模板（直接可用）

```bash
exec: PROJECT="[PROJECT]" /Library/Developer/CommandLineTools/usr/bin/python3 - <<'PY'
import csv, json, os, pathlib, urllib.parse
from scrapling import Fetcher

project = os.environ["PROJECT"]
base = pathlib.Path.home() / "research" / project
candidates = base / "candidates.csv"
out_jsonl = base / "scrapling_extracts.jsonl"
out_log = base / "crawl_log.md"

rows = []
with candidates.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        try:
            score = float(r.get("relevance_score", "0") or 0)
        except Exception:
            score = 0
        if score >= 4:
            rows.append(r)

rows = rows[:10]
fetcher = Fetcher(auto_match=False)
ok, fail = 0, 0

def build_url(row):
    pid = (row.get("paper_id") or "").strip()
    src = (row.get("source") or "").strip().lower()
    title = (row.get("title") or "").strip()
    if src == "arxiv" and pid:
        return f"https://arxiv.org/abs/{pid}"
    if pid.startswith("10."):
        return f"https://doi.org/{pid}"
    q = urllib.parse.quote(title[:180])
    return f"https://www.semanticscholar.org/search?q={q}"

with out_jsonl.open("w", encoding="utf-8") as out:
    for row in rows:
        pid = (row.get("paper_id") or "").strip()
        url = build_url(row)
        item = {"paper_id": pid, "url": url, "status": "failed", "title": None, "snippet": None}
        try:
            page = fetcher.get(url, timeout=30)
            txt = (page.get_all_text() or "").strip()
            title_node = page.css_first("title")
            item["status"] = "ok" if page.status and int(page.status) < 400 else f"http_{page.status}"
            item["title"] = title_node.text.strip() if title_node else None
            item["snippet"] = txt[:1200]
            if item["status"] == "ok":
                ok += 1
            else:
                fail += 1
        except Exception as e:
            item["status"] = f"error:{type(e).__name__}"
            fail += 1
        out.write(json.dumps(item, ensure_ascii=False) + "\\n")

out_log.write_text(
    "# Scrapling Crawl Log\\n"
    f"- project: {project}\\n"
    f"- selected_papers: {len(rows)}\\n"
    f"- success: {ok}\\n"
    f"- failed: {fail}\\n",
    encoding="utf-8",
)
print(f"saved: {out_jsonl}")
print(f"saved: {out_log}")
PY
```

注意：
- 上述模板走本地 Python + Scrapling，不依赖 `scrapling mcp` 子命令
- 深挖模式不是替代 API 搜索，而是作为证据增强层

---

## 各源搜索命令

### 源 1: arXiv（首选 — 用已安装的 arxiv-watcher）

优先使用已安装的 arxiv-watcher 技能：
```
用 arxiv-watcher 搜索关键词 "[QUERY]"，限制类别 [cs.AI/cs.CL/cs.LG]，时间范围 [DATE_FROM] 到今天，最多 20 篇
```

备用 — 直接调 arXiv API：
```
web_fetch: { url: "http://export.arxiv.org/api/query?search_query=all:[QUERY]&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending", maxChars: 50000 }
```
注意：arXiv API 返回 XML/Atom 格式。提取 `<entry>` 中的 title, author, summary, id, published。

### 源 2: Semantic Scholar（引用数据最丰富）

**关键词搜索：**
```
web_fetch: { url: "https://api.semanticscholar.org/graph/v1/paper/search?query=[QUERY_URL_ENCODED]&limit=20&fields=paperId,title,authors,year,abstract,citationCount,externalIds,venue,openAccessPdf", maxChars: 50000 }
```

**按 arXiv ID 查详情：**
```
web_fetch: { url: "https://api.semanticscholar.org/graph/v1/paper/ARXIV:[PAPER_ID]?fields=title,abstract,authors,year,citationCount,venue,references.title,citations.title,openAccessPdf", maxChars: 40000 }
```

**按作者搜索：**
```
web_fetch: { url: "https://api.semanticscholar.org/graph/v1/author/search?query=[AUTHOR_NAME]&limit=5&fields=name,paperCount,citationCount,hIndex", maxChars: 10000 }
```

### 源 3: OpenAlex（最大开放学术数据库，无需 Key）

**关键词搜索：**
```
web_fetch: { url: "https://api.openalex.org/works?search=[QUERY_URL_ENCODED]&per_page=20&sort=relevance_score:desc&filter=from_publication_date:2024-01-01&select=id,doi,title,authorships,publication_year,cited_by_count,primary_location,abstract_inverted_index", maxChars: 50000 }
```

**按概念/领域过滤：**
```
web_fetch: { url: "https://api.openalex.org/works?search=[QUERY]&filter=concept.id:C154945302,from_publication_date:2024-01-01&per_page=20&sort=cited_by_count:desc", maxChars: 50000 }
```
常用 concept ID: C154945302 (AI), C108827166 (ML), C204321447 (NLP), C41008148 (CS)

**注意**：OpenAlex 返回 `abstract_inverted_index`（倒排索引格式），需要重组为正常文本：将 JSON 的 key(词) 按 value(位置) 排序拼接。如果重组困难，可跳过 abstract 只取其他字段。

### 源 4: PubMed（生物医学必用）

**搜索获取 ID 列表：**
```
web_fetch: { url: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=[QUERY_URL_ENCODED]&retmax=20&retmode=json&sort=date&mindate=2024&maxdate=2026", maxChars: 10000 }
```

**用 ID 获取详情（逗号分隔多个 ID）：**
```
web_fetch: { url: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=[ID1],[ID2],[ID3]&retmode=json", maxChars: 50000 }
```

PubMed 是两步操作：先搜 ID，再查详情。

### 源 5: CrossRef（按 DOI 查引用/元数据最权威）

**关键词搜索：**
```
web_fetch: { url: "https://api.crossref.org/works?query=[QUERY_URL_ENCODED]&rows=20&sort=relevance&filter=from-pub-date:2024-01-01&select=DOI,title,author,published-print,is-referenced-by-count,abstract,container-title", maxChars: 50000 }
```

**按 DOI 精确查询：**
```
web_fetch: { url: "https://api.crossref.org/works/[DOI_URL_ENCODED]", maxChars: 20000 }
```

### 源 6: DBLP（计算机科学最全）

**搜索：**
```
web_fetch: { url: "https://dblp.org/search/publ/api?q=[QUERY_URL_ENCODED]&format=json&h=20", maxChars: 30000 }
```

DBLP 返回字段: title, authors (array), venue, year, doi, url。无 abstract 和引用数——需配合 Semantic Scholar 补充。

### 源 7: Europe PMC（生命科学 + 开放获取）

**搜索：**
```
web_fetch: { url: "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=[QUERY_URL_ENCODED]&format=json&pageSize=20&sort=RELEVANCE&resultType=core", maxChars: 50000 }
```

返回: title, authorString, journalTitle, pubYear, citedByCount, doi, abstractText, pmid。

### 源 8: bioRxiv（生物学预印本）

**按日期范围搜索（格式: YYYY-MM-DD）：**
```
web_fetch: { url: "https://api.biorxiv.org/details/biorxiv/[DATE_FROM]/[DATE_TO]/0/20", maxChars: 50000 }
```

**注意**：bioRxiv API 不支持关键词搜索，只支持按日期范围浏览。获取结果后需自行过滤标题和摘要中的关键词。非生物方向可跳过此源。

### 源 9: Papers with Code（带代码实现的 ML 论文）

**搜索：**
```
web_fetch: { url: "https://paperswithcode.com/api/v1/papers/?q=[QUERY_URL_ENCODED]&items_per_page=20&ordering=-proceeding", maxChars: 40000 }
```

**获取论文代码仓库：**
```
web_fetch: { url: "https://paperswithcode.com/api/v1/papers/[PAPER_ID]/repositories/", maxChars: 10000 }
```

适合寻找有开源实现的论文，特别是 ML/DL 方向。

---

## 补充搜索（已安装工具）

如果以上 API 返回不足，用已安装的 skill 补充：

**tavily-search（AI 优化跨源搜索）：**
```
用 tavily-search 搜索 "academic paper: [QUERY] site:arxiv.org OR site:semanticscholar.org"
```

**deep-research（复杂主题深挖，token 消耗高，慎用）：**
```
用 deep-research 调研 "[TOPIC]"，重点关注学术论文和技术报告
```

**browser（JS 重页面兜底）：**
当 web_fetch 返回乱码或空内容时（Google Scholar 等），用 `browser --profile cdp` 工具（必须使用 `cdp` profile，不是默认 profile，也不允许空 profile）。
如果 browser 报错 `profile not running`，先执行 `bash scripts/start-chrome-cdp.sh` 或 `bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh`。
如果用 OpenClaw 原生命令抓取，按 `open -> evaluate -> close` 执行；不要让学术站搜索页长期停留不关。

---

## 相关性评分标准

对每篇论文评 1-5 分。同时计算加权分（可选，给 Lead 做参考）：

| 分数 | 含义 | 标准 |
|------|------|------|
| 5 | 核心论文 | 直接回答研究问题，方法完全匹配 |
| 4 | 高度相关 | 方法或问题紧密相关，值得精读 |
| 3 | 有参考价值 | 背景知识或间接相关 |
| 2 | 边缘相关 | 仅部分主题重叠，一般不收录 |
| 1 | 不相关 | 不记录 |

加分因素（在基础分上 +0.5，不超过 5）：
- 引用数 > 100 且发表 < 2 年
- 来自顶会（NeurIPS, ICML, ACL, CVPR, ICLR 等）
- 有开源代码

---

## 输出格式

### 创建项目目录

```
exec: mkdir -p ~/research/[PROJECT]/{papers,notes}
```

### candidates.csv（必须输出）

```
write: ~/research/[PROJECT]/candidates.csv
```

严格使用此 header：
```csv
paper_id,title,authors,year,source,venue,citation_count,relevance_score,has_code,abstract_snippet
```

禁止输出自定义 header。若你手头已有非标准列，先映射回标准 10 列再写文件。

字段规则：
- `paper_id`: arXiv ID（如 2301.12345）或 DOI 或 S2 paper ID
- `authors`: 分号分隔，姓在前（如 "Smith J;Lee K"）
- `source`: arxiv | semantic_scholar | openalex | pubmed | crossref | dblp | europepmc | biorxiv | paperswithcode
- `venue`: 发表场所（如 "NeurIPS 2024"、"arXiv preprint"）
- `relevance_score`: 1-5 浮点数（含加分后的）
- `has_code`: yes | no | unknown
- `abstract_snippet`: 前 150 字符，内部逗号替换为分号

即使只找到少量论文，也必须写出合法 CSV（至少包含 header + 可用行）。
如果确实 0 结果，也必须写 header，并在 `search_log.md` 说明失败原因与已尝试的兜底路径。

### search_log.md（推荐输出）

```
write: ~/research/[PROJECT]/search_log.md
```

```markdown
# Search Log: [PROJECT]
Date: [YYYY-MM-DD]

## Query 1: "[query text]"
- arXiv: X results
- Semantic Scholar: Y results
- OpenAlex: Z results
- Total unique after dedup: N

## Query 2: "[query text]"
...

## Summary
- Total queries: N
- Total raw results: X
- After dedup: Y
- Score >= 3: Z (saved to candidates.csv)
- Score >= 4: W (recommended for deep analysis)
- Fallback triggered: [yes/no]
- Fallback reason: [network block / rate-limit / empty responses / none]
- Network block signature: [Blocked: resolves to private/internal/special-use IP address / none]
```

### 深挖模式附加输出（开启时必须有）

```
write: ~/research/[PROJECT]/crawl_log.md
write: ~/research/[PROJECT]/scrapling_extracts.jsonl
```

- `crawl_log.md`：记录抓取尝试数、成功数、失败数
- `scrapling_extracts.jsonl`：每行一个 JSON，至少包含 `paper_id/url/status/snippet`
- 在 `search_log.md` 末尾追加 `Scrapling Deep Crawl Summary` 小节

---

## 去重逻辑

同一篇论文可能出现在多个源中。去重规则：

1. **arXiv ID 匹配**：如果两条结果的 arXiv ID 相同 → 保留引用数更高的那条
2. **DOI 匹配**：DOI 相同 → 合并
3. **标题模糊匹配**：标题相似度 > 90%（忽略大小写和标点）→ 保留来源更权威的

去重后在 search_log.md 中记录合并了多少条。

---

## 速率限制速查

| 源 | 限制 | 建议间隔 |
|----|------|---------|
| arXiv | 3 秒/次 | `exec: sleep 3` |
| Semantic Scholar (有 key) | 100 次/5 分钟 | `exec: sleep 1` |
| Semantic Scholar (无 key) | 10 次/5 分钟 | `exec: sleep 30` |
| OpenAlex | 无硬限（有 email 更宽松） | `exec: sleep 1` |
| PubMed | 3 次/秒 | `exec: sleep 1` |
| CrossRef | 友好限制 | `exec: sleep 1` |
| DBLP | 宽松 | `exec: sleep 1` |
| Europe PMC | 宽松 | `exec: sleep 1` |
| bioRxiv | 宽松 | `exec: sleep 2` |
| Papers with Code | 宽松 | `exec: sleep 1` |

---

## 故障处理

| 问题 | 处理 |
|------|------|
| 任何 API 返回 429 | 等 60 秒再试 |
| 任何 API 返回 5xx | 跳过该源，用其他源补充 |
| OpenAlex abstract 是倒排索引 | 跳过 abstract，只用其他字段 |
| bioRxiv 不支持关键词搜索 | 拿到结果后用标题/摘要关键词过滤 |
| DBLP 无 abstract | 用 paper_id 到 Semantic Scholar 补充 |
| PubMed 需要两步查询 | 先 esearch 拿 ID，再 esummary 拿详情 |
| web_fetch 返回空/乱码 | 换用 browser 工具或 tavily-search |
| 所有方法都无结果 | 扩大关键词范围或报告"该方向论文稀少" |
