---
name: paper-analyzer
description: 从学术论文中提取结构化信息，生成标准化笔记和文献对比矩阵
metadata: {"openclaw": {}}
---

# Paper Analyzer Skill

精读论文，提取结构化信息。使用本机已安装的 summarize、web_fetch 等工具。

> ⚠️ 每次执行分析任务前，完整阅读本文件。严格使用下面的模板。

## 获取论文内容（按优先级尝试）

### 途径 1: 本地 PDF
```
read: ~/research/[PROJECT]/papers/[PAPER_ID].pdf
```

### 途径 2: arXiv 摘要页
```
web_fetch: { url: "https://arxiv.org/abs/[PAPER_ID]", extractMode: "markdown", maxChars: 30000 }
```

### 途径 3: Semantic Scholar API（含引用关系）
```
web_fetch: { url: "https://api.semanticscholar.org/graph/v1/paper/ARXIV:[PAPER_ID]?fields=title,abstract,authors,year,citationCount,venue,references.title,references.year,citations.title,citations.year,openAccessPdf", maxChars: 40000 }
```

### 途径 4: 按标题搜索（非 arXiv 论文）
```
web_fetch: { url: "https://api.semanticscholar.org/graph/v1/paper/search?query=[TITLE_URL_ENCODED]&limit=1&fields=title,abstract,authors,year,citationCount,venue,references.title,citations.title", maxChars: 30000 }
```

### 途径 5: OpenAlex 按 DOI 查询
```
web_fetch: { url: "https://api.openalex.org/works/doi:[DOI]?select=id,title,authorships,publication_year,cited_by_count,abstract_inverted_index,primary_location", maxChars: 30000 }
```

### 途径 6: summarize（长文提炼）

当拿到完整论文但内容太长时，用已安装的 summarize 技能：
```
用 summarize 提取这篇论文的核心方法和关键结果：[PAPER_URL_OR_PATH]
```

## 笔记模板

对每篇论文，写入 `~/research/[PROJECT]/notes/[PAPER_ID].md`：
笔记必须以 YAML frontmatter 开头，至少包含 `paper_id`、`title`、`relevance_score`。

```markdown
---
paper_id: "[arXiv ID 或 DOI]"
title: "[论文标题]"
relevance_score: 5
year: [YYYY]
source: "[arxiv | semantic_scholar | openalex | pubmed | crossref | dblp | europe_pmc | biorxiv | paperswithcode]"
authors: "[Author1, Author2, ...]"
venue: "[Conference/Journal 或 arXiv preprint]"
citation_count: [number]
retrieval_status: "[FULL_TEXT | ABSTRACT_ONLY | ACCESS_FAILED]"
---

## Summary
[1-3 句话：这篇论文的核心问题、方法与结论概览]

## Research Question
[1-3 句话：这篇论文要解决什么问题？]

## Methodology
[3-5 句话：提出了什么方法/模型/框架？]

## Key Findings
| 指标 | 数据集 | 数值 | 对比基线 |
|------|--------|------|----------|
| [metric] | [dataset] | [value] | [+/- vs baseline] |

## Contributions
1. [贡献 1]
2. [贡献 2]
3. [贡献 3，如有]

## Limitations
- [局限 1]
- [局限 2]

## Key Citations
- [论文标题] ([年份])
- [论文标题] ([年份])
- [论文标题] ([年份])

## Tags
[逗号分隔，如: multi-agent, retrieval, LLM, benchmark]

## BibTeX
```bibtex
@article{[citekey],
  title={[title]},
  author={[authors]},
  year={[year]},
  journal={[venue]},
  url={[url]}
}
```
```

### 字段规则

- frontmatter 和各章节都必须填写，信息不可用时写 **N/A**，绝不留空
- "关键结果"表至少 1 行，无定量结果时写 `N/A | N/A | N/A | N/A`
- `retrieval_status` 必填——告诉 review-lead 哪些论文需要找替代途径
- 永远不要编造论文中没有的数据

## 对比矩阵格式

所有论文分析完后，写入 `~/research/[PROJECT]/matrix.csv`：

```csv
paper_id,title,year,method,dataset,metric,result,category,strengths,limitations
```

字段说明：
- `paper_id`、`method`、`dataset`、`category` 是 engine validator 的必填列，列名必须精确匹配
- `method`: 核心方法或框架名（如 MADDPG; survey; graph MARL）
- `dataset`: 主要实验数据集或场景，无则写 `N/A`
- `metric`: 主要评估指标名，无则写 `N/A`
- `result`: 主要结果值或结论，无则写 `N/A`
- `category`: 主题分类（如 survey; theory; robotics; LLM-agents; mean-field）
- `strengths`: 一句话概括该论文最强贡献（不用逗号，用分号）
- `limitations`: 一句话概括局限（不用逗号，用分号）

## 批量处理规则

1. 逐篇处理，每完成一篇立即写入笔记（不要攒到最后）
2. 如果某篇获取失败，写一个最简笔记（获取状态 = ACCESS_FAILED），然后继续
3. 所有笔记写完后，一次性生成 matrix.csv
4. 每轮最多处理 30 篇

## 常见问题

| 问题 | 处理 |
|------|------|
| arXiv 返回 HTML 而非内容 | 改用 Semantic Scholar API |
| Semantic Scholar 返回 429 | 等 60 秒重试 |
| PDF 太大无法 read | 改用 arXiv 摘要页 + summarize |
| 非 arXiv 论文 | 按标题在 Semantic Scholar 搜索，或用 DOI 查 OpenAlex |
| 倒排索引格式的 abstract | 跳过 abstract 重组，从其他源获取 |
