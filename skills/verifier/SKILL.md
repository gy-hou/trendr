---
name: verifier
description: Independent verification of literature review quality — citation checks, claim tracing, coverage analysis
metadata: {"openclaw": {}}
---

# Verifier Skill

独立验证文献综述质量。只读检查，不修改任何文件。

> ⚠️ 执行验证前，完整阅读本文件。

## Runtime Router（必读）

识别当前 runtime，只读取对应 sibling，另一方休眠：

- `openclaw`    → 本文件内原有指令块仍然有效（`web_fetch:` / `exec:` / `openclaw browser`）
- `claude-code` → **跳过本文件的指令块**，读 `./claude-code.md` 获取 Claude Code 原生工具调用方式
- `codex` / `cli` → 参考 `./claude-code.md`（命名与 HTTP 工具最接近，必要时进一步降级）

本节之后的章节描述 **共享知识**（源、字段契约、评分规则、故障处理）。指令块保持现状（OpenClaw 语法），Claude Code 读者请切换到 `./claude-code.md`。

## 角色

Verifier 是流水线中唯一的质量关卡。它在 WRITING 完成后、DONE 之前运行。
它不写综述、不改引用、不做主观评价。它只输出 `verify.json`。

## 输入文件

验证前必须读取全部文件：

```
read: ~/research/[PROJECT]/review.md
read: ~/research/[PROJECT]/references.bib
read: ~/research/[PROJECT]/candidates.csv
read: ~/research/[PROJECT]/matrix.csv
exec: ls ~/research/[PROJECT]/notes/
```

然后逐个读取 `notes/` 下的笔记文件。

## 检查项

### 1. citation_existence（severity: error）

**规则**：review.md 中每个 `\cite{key}` 在 references.bib 中都有对应的 `@entry{key,`。

**方法**：
1. 正则提取 review.md 中所有 `\cite{key1, key2}` → 展平为 key 列表
2. 正则提取 references.bib 中所有 `@type{key,` → key 集合
3. 差集 = 缺失引用

### 2. citation_reality（severity: error）

**规则**：references.bib 中每条 entry 对应真实论文。

**方法**：
1. 将 bib entry 的 key 与 candidates.csv 的 paper_id 交叉比对
2. 对不在 candidates.csv 中的 entry，抽样 5 条通过 Semantic Scholar API 验证：
   ```
   GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}
   ```
3. 返回 404 或完全不匹配 → 标记为 phantom paper

### 3. claim_support（severity: warning / error）

**规则**：review.md 中包含 `\cite{key}` 的事实性语句，能在对应 notes/{id}.md 中找到支撑。

**方法**：
1. 提取 review.md 中含 citation 的句子
2. 对每个 citation key，查找对应 notes 文件
3. 检查 notes 中是否有与 claim 相关的内容（关键词匹配 + 语义相似度判断）
4. 找不到支撑 → warning
5. 如果 `notes/` 目录缺失、为空、或缺少对应 citekey 的 note → **error**

### 4. coverage（severity: warning）

**规则**：candidates.csv 中 relevance_score >= 4 的论文，应当在 review.md 中被提及。

**方法**：
1. 从 candidates.csv 筛选 relevance_score >= 4 的 paper_id
2. 从 review.md 提取所有被引用的 paper_id
3. 差集 = 未覆盖的高相关论文

### 5. taxonomy_consistency（severity: error）

**规则**：review.md Taxonomy 表格中的 Category 与 Detailed Analysis 的章节标题一致。

**方法**：
1. 解析 `## 2. Taxonomy` 下的 Markdown 表格 → 提取 Category 列
2. 解析 `## 3. Detailed Analysis` 下的 `### 3.x` 子标题
3. 两者必须一一对应（允许顺序不同）

### 6. bib_quality（severity: warning）

**规则**：每条 BibTeX entry 至少包含 title、author、year。

**方法**：
1. 解析每个 `@type{key, ... }` 块
2. 检查是否存在 `title = `, `author = `, `year = ` 字段
3. 缺失字段 → warning

## 输出格式

写入 `~/research/[PROJECT]/verify.json`：

```jsonc
{
  "pass": false,            // 所有 error 级检查通过 → true；任一 error 失败 → false
  "run_id": "...",
  "checked_at": "2026-04-01T15:10:00Z",
  "summary": "2 errors, 1 warning",
  "issues": [
    {
      "check": "citation_reality",
      "severity": "error",
      "citekey": "smith2024foo",
      "reason": "not in candidates.csv"
    },
    {
      "check": "citation_reality",
      "severity": "error",
      "citekey": "jones2023bar",
      "reason": "Semantic Scholar returned 404"
    },
    {
      "check": "bib_quality",
      "severity": "warning",
      "citekey": "metagpt2025",
      "reason": "author field is N/A"
    }
  ],
  "checks": {
    "citation_existence": {
      "pass": true,
      "severity": "error",
      "details": "32/32 citations found in references.bib"
    },
    "citation_reality": {
      "pass": false,
      "severity": "error",
      "details": "2 entries not found in candidates.csv",
      "issues": [
        {"citekey": "smith2024foo", "reason": "not in candidates.csv"},
        {"citekey": "jones2023bar", "reason": "Semantic Scholar returned 404"}
      ]
    },
    "claim_support": {
      "pass": true,
      "severity": "warning",
      "details": "28/30 claims have supporting notes"
    },
    "coverage": {
      "pass": true,
      "severity": "warning",
      "details": "All relevance >= 4 papers mentioned"
    },
    "taxonomy_consistency": {
      "pass": true,
      "severity": "error",
      "details": "4 categories match 4 section headers"
    },
    "bib_quality": {
      "pass": true,
      "severity": "warning",
      "details": "32/32 entries have required fields"
    }
  }
}
```

## 判定规则

- `pass = true` 当且仅当所有 severity=error 的检查通过
- `issues` 是所有 `pass=false` 检查的 `issues` 列表做扁平合并后的结果
- 每条 issue 必须包含 `check`（来源检查名）和 `severity`
- 如果某个 `pass=false` 的检查没有细粒度 `issues`，也要生成一条 issue：
  `{"check": "taxonomy_consistency", "severity": "error", "reason": "categories don't match section headers"}`
- `issues` 数组可以为空（当所有 checks pass 时），但字段必须存在
- warning 不阻塞流水线，但会被记录
- 如果 `pass = false`，状态机会将流水线回退到 WRITING 进行修复（最多 2 轮）

## 禁止事项

- 不修改 review.md 或 references.bib
- 不添加或删除引用
- 不改变分类体系
- 不做主观质量判断（如"写得不清楚"）
- 不编造验证结果
