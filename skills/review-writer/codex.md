---
runtime: codex
parent_skill: review-writer
allowed-tools:
  - exec_command
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（综述结构模板、质量清单、BibTeX 规范）见同目录 `SKILL.md`。本文件只描述 Codex 工具调用方式。

## 使用方法

写综述前必须先读取所有输入文件，再按 `SKILL.md` §综述结构模板 起草：

1. `exec_command(cmd="ls ~/research/[PROJECT]/notes/")`
2. 读取 `matrix.csv`、`candidates.csv`、`search_log.md`（若存在）
3. 逐个读取 `notes/` 下的笔记
4. 起草 `review.md`
5. 生成 `references.bib`

## 指令映射

| OpenClaw 原语 | Codex 等价 |
|--------------|-----------|
| `exec: ls ~/research/[PROJECT]/notes/` | `exec_command(cmd=\"ls ~/research/[PROJECT]/notes/\")` |
| `read: ~/research/[PROJECT]/matrix.csv` | `exec_command(cmd=\"sed -n '1,200p' ~/research/[PROJECT]/matrix.csv\")` |
| `write: ~/research/[PROJECT]/review.md` | 调用现有脚本或 `exec_command` 原子写入 |

## 兜底链

- `notes/` 为空：仅凭 `candidates.csv` 摘要字段写综述，明确标注 `基于摘要，未精读全文`
- 引用仍未确认：保留可验证占位符，交给 `verifier` 阶段核查

## Codex 限制

- 不在写作阶段补抓引用网页；联网核验属于 `verifier` 职责。
- 最终产物必须是落盘文件，不是仅在回复里给出草稿。
