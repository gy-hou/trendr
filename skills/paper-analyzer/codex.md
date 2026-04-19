---
runtime: codex
parent_skill: paper-analyzer
allowed-tools:
  - exec_command
  - web
  - spawn_agent
  - wait_agent
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（字段契约、笔记模板、矩阵格式）见同目录 `SKILL.md`。本文件只描述 Codex 工具调用方式。

## 使用方法

对 `candidates.csv` 中的高分论文执行精读分析：

1. 用 `exec_command` 读取 `candidates.csv`。
2. 对每篇论文按优先级获取内容：本地 PDF → arXiv → Semantic Scholar → OpenAlex。
3. 按 `SKILL.md` §笔记模板 提取结构化字段。
4. 将每篇笔记落盘到 `notes/[paper_id].md`，再汇总更新 `matrix.csv`。

## 指令映射

| OpenClaw 原语 | Codex 等价 |
|--------------|-----------|
| `read: ~/research/.../papers/[PAPER_ID].pdf` | `exec_command(cmd=\"pdftotext ...\" )`、现有 PDF 解析脚本，或本地摘要页兜底 |
| `web_fetch: { url: \"https://arxiv.org/abs/[ID]\" }` | `exec_command(cmd='curl -fsSL \"https://arxiv.org/abs/[ID]\"')` 或 `web.open` |
| `web_fetch: { url: \"https://api.semanticscholar.org/...\" }` | `exec_command(cmd='curl -fsSL \"https://api.semanticscholar.org/...\"')` |
| `write: ~/research/.../notes/[ID].md` | 用现有脚本或 `exec_command` 原子写入文件 |

## 获取论文内容

1. **本地 PDF**：优先用本地文件，避免重复联网。
2. **arXiv 摘要页**：
   ```text
   exec_command(cmd='curl -fsSL "https://arxiv.org/abs/[PAPER_ID]"')
   ```
3. **Semantic Scholar API**：
   ```text
   exec_command(cmd='curl -fsSL "https://api.semanticscholar.org/graph/v1/paper/ARXIV:[PAPER_ID]?fields=title,abstract,authors,year,citationCount,venue,references.title,citations.title,openAccessPdf"')
   ```
4. **OpenAlex**（DOI 可用时）：
   ```text
   exec_command(cmd='curl -fsSL "https://api.openalex.org/works/doi:[DOI]?select=id,title,authorships,publication_year,cited_by_count,abstract_inverted_index,primary_location"')
   ```

## 兜底链

- 全部 API 失败：仅基于 `candidates.csv` 现有摘要写笔记，并标 `source: abstract_only`
- PDF 无法解析：降级到摘要页 / API 元数据
- 默认串行分析；只有用户明确要求并行，才可按 disjoint paper 批次使用 `spawn_agent`

## Codex 限制

- 不搜索新论文；只分析 `candidates.csv` 里已有条目。
- 不修改 `candidates.csv`。
- 输出必须落盘为 `notes/*.md` 与 `matrix.csv`，不能只返回摘要。
