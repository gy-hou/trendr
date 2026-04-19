---
name: research-vault
description: 将研究成果持久化到 Obsidian vault，维护论文池索引。支持每日研究日志、论文卡片、综述归档，以及跨项目论文去重和快速检索。
---

# Research Vault Skill

将文献综述成果持久化到 Obsidian vault，维护可检索的论文索引池。

> ⚠️ 使用前请完整阅读本文件。

## Runtime Router（必读）

识别当前 runtime，只读取对应 sibling，另一方休眠：

- `openclaw`    → 本文件内原有指令块仍然有效（`web_fetch:` / `exec:` / `openclaw browser`）
- `claude-code` → **跳过本文件的指令块**，读 `./claude-code.md` 获取 Claude Code 原生工具调用方式
- `codex` / `cli` → **跳过本文件的指令块**，读 `./codex.md` 获取 Codex 原生工具调用方式

本节之后的章节描述 **共享知识**（源、字段契约、评分规则、故障处理）。指令块保持现状（OpenClaw 语法），Claude Code 读者请切换到 `./claude-code.md`，Codex/CLI 读者请切换到 `./codex.md`。

## 设计原则

- **Obsidian vault** = 你的永久知识库（论文卡片、综述、每日日志）
- **~/research/** = OpenClaw 的临时工作空间（每个项目用完可清理）
- **论文池索引** = Obsidian vault 内的持久化 CSV，跨项目去重和检索

## Vault 结构

```
[VAULT_PATH]/Research/
├── _index/
│   └── paper-pool.csv          ← 论文池索引（所有项目累积）
├── papers/                     ← 论文卡片（每篇论文一个 .md）
│   ├── 2301.12345.md
│   └── ...
├── reviews/                    ← 综述归档
│   ├── rl-multi-agent-finance/
│   │   ├── review.md
│   │   └── references.bib
│   └── ...
├── daily/                      ← 每日研究日志
│   ├── 2026-03-10.md
│   └── ...
└── templates/                  ← 模板（自动创建）
    ├── paper-card.md
    └── daily-research.md
```

默认 vault 路径: `~/Documents/OpenClaw-Vault`（工作用 vault）

## 初始化（首次使用）

```bash
exec: VAULT="$HOME/Documents/OpenClaw-Vault"
exec: mkdir -p "$VAULT/Research/"{_index,papers,reviews,daily,templates}
```

创建论文池索引（如果不存在）：
```bash
exec: VAULT="$HOME/Documents/OpenClaw-Vault" && \
  POOL="$VAULT/Research/_index/paper-pool.csv" && \
  [ ! -f "$POOL" ] && echo "paper_id,title,authors,year,venue,source,citation_count,doi,project,added_date,tags,status" > "$POOL" && echo "Created" || echo "Already exists"
```

创建模板：
```bash
write: [VAULT]/Research/templates/paper-card.md
```
内容见下方"论文卡片模板"。

---

## 操作 1: 同步论文到索引池

每次文献搜索完成后（Phase 1 结束），将 candidates.csv 合并到论文池：

```bash
exec: VAULT="$HOME/Documents/OpenClaw-Vault" && \
  POOL="$VAULT/Research/_index/paper-pool.csv" && \
  PROJECT="[PROJECT_NAME]" && \
  CANDIDATES="$HOME/research/$PROJECT/candidates.csv" && \
  tail -n +2 "$CANDIDATES" | while IFS=, read -r pid title authors year source venue citations score has_code abstract; do \
    if ! grep -q "^$pid," "$POOL" 2>/dev/null; then \
      echo "$pid,$title,$authors,$year,$venue,$source,$citations,,$PROJECT,$(date +%Y-%m-%d),,$score" >> "$POOL"; \
    fi; \
  done && \
  echo "Pool updated. Total entries: $(tail -n +2 "$POOL" | wc -l | tr -d ' ')"
```

**去重规则**：按 paper_id 第一列匹配，已存在的论文不会被重复添加。跨项目搜到同一篇论文时，只保留首次记录。

---

## 操作 2: 生成论文卡片到 Obsidian

将 notes/ 下的分析笔记转为 Obsidian 格式的论文卡片：

对每篇已分析的论文，写入 `[VAULT]/Research/papers/[PAPER_ID].md`：

```markdown
---
paper_id: "[PAPER_ID]"
title: "[TITLE]"
authors: [AUTHORS]
year: [YEAR]
venue: "[VENUE]"
citations: [N]
project: "[PROJECT]"
tags: [tag1, tag2, tag3]
status: analyzed
created: [YYYY-MM-DD]
---

# [TITLE]

> **来源**: [[reviews/[PROJECT]/review|[PROJECT] 综述]]
> **池索引**: 见 [[_index/paper-pool|论文池]]

## 研究问题
[从 notes 复制]

## 方法
[从 notes 复制]

## 关键结果
[从 notes 复制]

## 主要贡献
[从 notes 复制]

## 局限性
[从 notes 复制]

## 关键引用
[从 notes 复制，用 [[]] 链接已有卡片]

## BibTeX
[从 notes 复制]
```

**用 obsidian-cli 创建**：
```bash
exec: obsidian-cli create --vault "[VAULT_PATH]" --path "Research/papers/[PAPER_ID].md" --content "$(cat /tmp/paper-card-content.md)"
```

或者直接用 write 工具写入 vault 路径：
```bash
write: [VAULT]/Research/papers/[PAPER_ID].md
```

---

## 操作 3: 归档综述报告

项目综述完成后，将 review.md 和 references.bib 复制到 vault：

```bash
exec: VAULT="$HOME/Documents/OpenClaw-Vault" && \
  PROJECT="[PROJECT_NAME]" && \
  mkdir -p "$VAULT/Research/reviews/$PROJECT" && \
  cp "$HOME/research/$PROJECT/review.md" "$VAULT/Research/reviews/$PROJECT/" && \
  cp "$HOME/research/$PROJECT/references.bib" "$VAULT/Research/reviews/$PROJECT/" && \
  cp "$HOME/research/$PROJECT/matrix.csv" "$VAULT/Research/reviews/$PROJECT/" && \
  echo "Archived to $VAULT/Research/reviews/$PROJECT/"
```

---

## 操作 4: 写每日研究日志

每次研究会话结束时，写一条日志到 Obsidian：

```bash
write: [VAULT]/Research/daily/[YYYY-MM-DD].md
```

```markdown
---
date: [YYYY-MM-DD]
projects: [[PROJECT]]
papers_found: [N]
papers_analyzed: [N]
---

# 研究日志 [YYYY-MM-DD]

## 今日进展
- **项目**: [[reviews/[PROJECT]/review|[PROJECT]]]
- **搜索**: [N] 篇候选 → [M] 篇精读
- **新发现**: [1-2 句关键发现]

## 值得关注的论文
- [[papers/2301.12345|论文标题]] — [一句话理由]
- [[papers/2302.67890|论文标题]] — [一句话理由]

## 明日计划
- [下一步]
```

---

## 操作 5: 检索论文池

从论文池中查找论文（按关键词、作者、项目、标签等）：

**按关键词搜标题**：
```bash
exec: grep -i "[KEYWORD]" "$HOME/Documents/OpenClaw-Vault/Research/_index/paper-pool.csv" | head -20
```

**按作者搜**：
```bash
exec: awk -F',' '$3 ~ /[AUTHOR_NAME]/' "$HOME/Documents/OpenClaw-Vault/Research/_index/paper-pool.csv"
```

**按项目筛选**：
```bash
exec: awk -F',' '$9 == "[PROJECT]"' "$HOME/Documents/OpenClaw-Vault/Research/_index/paper-pool.csv"
```

**统计**：
```bash
exec: POOL="$HOME/Documents/OpenClaw-Vault/Research/_index/paper-pool.csv" && \
  echo "总论文数: $(tail -n +2 "$POOL" | wc -l | tr -d ' ')" && \
  echo "项目分布:" && awk -F',' 'NR>1 {print $9}' "$POOL" | sort | uniq -c | sort -rn && \
  echo "年份分布:" && awk -F',' 'NR>1 {print $4}' "$POOL" | sort | uniq -c | sort -rn
```

**按 paper_id 查完整信息**：
```bash
exec: grep "^[PAPER_ID]," "$HOME/Documents/OpenClaw-Vault/Research/_index/paper-pool.csv"
```

如果论文已有 Obsidian 卡片，可以告诉用户：
> 详细分析见 Obsidian: `Research/papers/[PAPER_ID].md`

---

## 论文池 CSV 字段说明

```
paper_id     — arXiv ID / DOI / S2 ID（主键，唯一）
title        — 论文标题
authors      — 作者（分号分隔）
year         — 发表年份
venue        — 发表场所
source       — 搜索来源（arxiv/semantic_scholar/openalex/...）
citation_count — 引用数
doi          — DOI（可为空）
project      — 首次发现该论文的项目名
added_date   — 加入日期
tags         — 标签（分号分隔）
status       — candidate / analyzed / cited_in_review
```

`status` 字段由后续流程更新：
- `candidate` — 搜索发现但未精读
- `analyzed` — 已有 notes
- `cited_in_review` — 在综述中被引用

---

## 完整工作流集成

在文献综述的每个阶段之后调用对应操作：

| 阶段 | 操作 |
|------|------|
| Phase 1 搜索完成 | **操作 1** — 同步到论文池 |
| Phase 2 精读完成 | **操作 2** — 生成论文卡片 |
| Phase 4 综述完成 | **操作 3** — 归档综述报告 |
| 会话结束 | **操作 4** — 写每日日志 |
| 任何时候查论文 | **操作 5** — 检索论文池 |

---

## Vault 路径自定义

- **工作 vault**: `~/Documents/OpenClaw-Vault`（默认）
- **个人 vault**: `~/Documents/Obsidian Vault`

如果需要切换 vault：
```bash
ln -s /your/actual/vault/path ~/Documents/OpenClaw-Vault
```
