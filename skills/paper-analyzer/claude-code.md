---
runtime: claude-code
parent_skill: paper-analyzer
allowed-tools:
  - Read
  - Write
  - Bash
  - WebFetch
  - Agent
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md` 的原生指令块。
> 共享知识（字段契约、笔记模板、矩阵格式）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

对 `candidates.csv` 中的每篇高分论文执行精读分析：

1. `Read(file_path="~/research/[PROJECT]/candidates.csv")` 读取候选列表
2. 对每篇论文按以下优先级获取内容（见下方指令映射）
3. 按 `SKILL.md` §笔记模板 提取结构化字段
4. `Write` 笔记到 `~/research/[PROJECT]/notes/[PAPER_ID].md`
5. 汇总更新 `matrix.csv`

## 指令映射

| OpenClaw 原语 | Claude Code 等价 |
|--------------|----------------|
| `read: ~/research/.../papers/[PAPER_ID].pdf` | `Read(file_path="~/research/[PROJECT]/papers/[PAPER_ID].pdf")` |
| `web_fetch: { url: "https://arxiv.org/abs/[ID]", extractMode: "markdown" }` | `WebFetch(url="https://arxiv.org/abs/[ID]", prompt="提取论文全文 markdown")` |
| `web_fetch: { url: "https://api.semanticscholar.org/..." }` | `WebFetch(url="https://api.semanticscholar.org/...", prompt="提取引用关系")` |
| `write: ~/research/.../notes/[ID].md` | `Write(file_path="~/research/[PROJECT]/notes/[ID].md", content=...)` |

## 获取论文内容（优先级）

1. **本地 PDF**：`Read(file_path="~/research/[PROJECT]/papers/[PAPER_ID].pdf")`
2. **arXiv 摘要页**：
   ```
   WebFetch(url="https://arxiv.org/abs/[PAPER_ID]", prompt="提取标题、摘要、作者、内容章节")
   ```
3. **Semantic Scholar API**（含引用）：
   ```
   WebFetch(
     url="https://api.semanticscholar.org/graph/v1/paper/ARXIV:[PAPER_ID]?fields=title,abstract,authors,year,citationCount,venue,references.title,citations.title,openAccessPdf",
     prompt="提取完整元数据和引用列表"
   )
   ```
4. **OpenAlex**（DOI 可用时）：
   ```
   WebFetch(url="https://api.openalex.org/works/doi:[DOI]?select=id,title,authorships,publication_year,cited_by_count,abstract_inverted_index,primary_location", prompt="提取结构化元数据")
   ```

## 兜底链

- 所有 API 都失败 → 仅凭 `candidates.csv` 中的摘要字段写笔记，标注 `source: abstract_only`
- PDF 无法解析 → `WebFetch` 抓取 HTML 版本

## Claude Code 限制

- PDF 读取依赖 `Read` 工具的文件内容解析能力；超大 PDF 建议只读摘要页。
- `Agent` 工具可用于并行分析多篇论文，但状态机默认串行执行，无需显式并发。
