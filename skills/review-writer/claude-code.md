---
runtime: claude-code
parent_skill: review-writer
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md` 的原生指令块。
> 共享知识（综述结构模板、质量清单、BibTeX 规范）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

写综述前必须先读取所有输入文件，再按 `SKILL.md` §综述结构模板 起草：

1. 列出 notes 目录：`Bash(command="ls ~/research/[PROJECT]/notes/")`
2. `Read(file_path="~/research/[PROJECT]/matrix.csv")`
3. `Read(file_path="~/research/[PROJECT]/candidates.csv")`
4. `Read(file_path="~/research/[PROJECT]/search_log.md")` （若存在）
5. 逐个 `Read` `notes/` 下的每个笔记文件
6. 按模板起草，`Write` 到 `~/research/[PROJECT]/review.md`
7. 生成 BibTeX，`Write` 到 `~/research/[PROJECT]/references.bib`

## 指令映射

| OpenClaw 原语 | Claude Code 等价 |
|--------------|----------------|
| `exec: ls ~/research/[PROJECT]/notes/` | `Bash(command="ls ~/research/[PROJECT]/notes/")` |
| `read: ~/research/[PROJECT]/matrix.csv` | `Read(file_path="~/research/[PROJECT]/matrix.csv")` |
| `write: ~/research/[PROJECT]/review.md` | `Write(file_path="~/research/[PROJECT]/review.md", content=...)` |

## 兜底链

- notes 为空 → 仅凭 `candidates.csv` 摘要字段写综述，标注 `⚠️ 基于摘要，未精读全文`
- 引用无法验证 → 先写占位符 `[CITE:title]`，verifier 阶段再检查

## Claude Code 限制

- 综述文件可能较大（>10k 字），`Write` 工具支持完整写入，不需要分块。
- 不使用 `WebFetch` 抓取引用（这是 verifier 的职责）。
