---
name: research-vault
description: 将研究成果自动持久化到 Obsidian vault，维护论文池索引。支持论文卡片、综述归档、每日日志、跨项目检索。
metadata: {"openclaw": {"requires": {"bins": ["obsidian-cli"]}}}
---

# Research Vault Skill

将文献综述成果自动持久化到 Obsidian vault，维护可检索的论文索引池。

> ⚠️ 使用前完整阅读。每次综述完成后 Phase 5 必须执行本 skill 的操作。

## Vault 路径

```
~/Documents/ObsidianVault
```

（此路径由安装脚本自动配置。如需修改请编辑 `.trendr-config`。）

## Vault 结构

```
[VAULT]/Research/
├── _index/paper-pool.csv    ← 论文池索引（所有项目累积，可检索）
├── papers/                  ← 论文卡片（每篇一个 .md）
├── reviews/                 ← 综述归档（按项目分目录）
├── daily/                   ← 每日研究日志
└── templates/               ← 模板
```

---

## 操作 1: 同步论文到索引池

**何时执行**: Phase 1（搜索）完成后

将 candidates.csv 合并到论文池，按 paper_id 去重：

```bash
exec: VAULT="~/Documents/ObsidianVault" && \
  POOL="$VAULT/Research/_index/paper-pool.csv" && \
  PROJECT="[PROJECT_NAME]" && \
  tail -n +2 ~/research/$PROJECT/candidates.csv | while IFS=, read -r pid title authors year source venue cites score code abstract; do \
    if [ -n "$pid" ] && ! grep -q "^$pid," "$POOL" 2>/dev/null; then \
      echo "$pid,$title,$authors,$year,$venue,$source,$cites,,$PROJECT,$(date +%Y-%m-%d),,candidate" >> "$POOL"; \
    fi; \
  done && \
  echo "Pool total: $(tail -n +2 "$POOL" | wc -l | tr -d ' ') papers"
```

---

## 操作 2: 生成论文卡片

**何时执行**: Phase 2（精读）完成后

对 notes/ 下每篇已分析的论文，创建 Obsidian 论文卡片。

对每个 `~/research/[PROJECT]/notes/[PAPER_ID].md`，读取内容然后写入 Obsidian：

```bash
write: ~/Documents/ObsidianVault/Research/papers/[PAPER_ID].md
```

卡片格式：

```markdown
---
paper_id: "[PAPER_ID]"
title: "[TITLE]"
authors: [AUTHORS]
year: [YEAR]
venue: "[VENUE]"
citations: [N]
project: "[PROJECT]"
tags: [tag1, tag2]
status: analyzed
created: [YYYY-MM-DD]
---

# [TITLE]

> **综述**: [[reviews/[PROJECT]/review|[PROJECT]]]
> **论文池**: [[_index/paper-pool|索引]]

## 研究问题
[从 note 复制]

## 方法
[从 note 复制]

## 关键结果
[从 note 复制]

## 主要贡献
[从 note 复制]

## 局限性
[从 note 复制]

## BibTeX
[从 note 复制]
```

同时更新论文池中该论文的 status 为 `analyzed`。

---

## 操作 3: 归档综述报告

**何时执行**: Phase 4（撰写）完成后

```bash
exec: VAULT="~/Documents/ObsidianVault" && \
  PROJECT="[PROJECT_NAME]" && \
  mkdir -p "$VAULT/Research/reviews/$PROJECT" && \
  cp ~/research/$PROJECT/review.md "$VAULT/Research/reviews/$PROJECT/" && \
  cp ~/research/$PROJECT/references.bib "$VAULT/Research/reviews/$PROJECT/" && \
  cp ~/research/$PROJECT/matrix.csv "$VAULT/Research/reviews/$PROJECT/" && \
  echo "Archived to Obsidian: Research/reviews/$PROJECT/"
```

---

## 操作 4: 写每日研究日志

**何时执行**: 每次研究会话结束时

```bash
write: ~/Documents/ObsidianVault/Research/daily/[YYYY-MM-DD].md
```

```markdown
---
date: [YYYY-MM-DD]
projects: ["[PROJECT]"]
papers_found: [N]
papers_analyzed: [M]
---

# 研究日志 [YYYY-MM-DD]

## 今日进展
- **项目**: [[reviews/[PROJECT]/review|[PROJECT]]]
- **搜索**: [N] 篇候选 → [M] 篇精读
- **新发现**: [关键发现]

## 值得关注的论文
- [[papers/[ID1]|论文标题]] — [理由]
- [[papers/[ID2]|论文标题]] — [理由]

## 下一步
- [计划]
```

如果当天日志已存在，在末尾追加而不是覆盖。

---

## 操作 5: 检索论文池

**何时执行**: 用户查找之前搜过的论文时

**按关键词**:
```bash
exec: grep -i "[KEYWORD]" ~/Documents/ObsidianVault/Research/_index/paper-pool.csv | head -20
```

**按作者**:
```bash
exec: awk -F',' '$3 ~ /[AUTHOR]/' ~/Documents/ObsidianVault/Research/_index/paper-pool.csv
```

**按项目**:
```bash
exec: awk -F',' '$9 == "[PROJECT]"' ~/Documents/ObsidianVault/Research/_index/paper-pool.csv
```

**统计**:
```bash
exec: POOL=~/Documents/ObsidianVault/Research/_index/paper-pool.csv && \
  echo "总论文: $(tail -n +2 "$POOL" | wc -l | tr -d ' ')" && \
  echo "--- 按项目 ---" && awk -F',' 'NR>1{print $9}' "$POOL" | sort | uniq -c | sort -rn && \
  echo "--- 按年份 ---" && awk -F',' 'NR>1{print $4}' "$POOL" | sort | uniq -c | sort -rn
```

有详细分析的论文，告诉用户：
> 详细分析见 Obsidian: Research/papers/[PAPER_ID].md

---

## 论文池 CSV 字段

| 字段 | 说明 |
|------|------|
| paper_id | 主键（arXiv ID / DOI / S2 ID） |
| title | 标题 |
| authors | 作者（分号分隔） |
| year | 年份 |
| venue | 发表场所 |
| source | 搜索来源 |
| citation_count | 引用数 |
| doi | DOI |
| project | 首次发现的项目名 |
| added_date | 加入日期 |
| tags | 标签（分号分隔） |
| status | candidate / analyzed / cited_in_review |
