---
runtime: codex
parent_skill: verifier
allowed-tools:
  - exec_command
  - web
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（验证维度、评分规则、verify.json schema）见同目录 `SKILL.md`。本文件只描述 Codex 工具调用方式。

## 使用方法

Verifier 是只读检查器，不修改任何研究文件，只输出 `verify.json`：

1. 读取 `review.md`、`references.bib`、`candidates.csv`、`matrix.csv`
2. 按 `SKILL.md` §验证清单 执行各维度检查
3. 需要联网核验时，优先 `exec_command` + `curl`，或 `web.open` 做页面级确认
4. 将结果写入 `verify.json`

## 指令映射

| OpenClaw 原语 | Codex 等价 |
|--------------|-----------|
| `read: ~/research/[PROJECT]/review.md` | `exec_command(cmd=\"sed -n '1,220p' ~/research/[PROJECT]/review.md\")` |
| `web_fetch: { url: \"https://arxiv.org/abs/[ID]\" }` | `exec_command(cmd='curl -fsSL \"https://arxiv.org/abs/[ID]\"')` 或 `web.open` |
| `write: ~/research/[PROJECT]/verify.json` | 用现有脚本或 `exec_command` 原子写入 |

## 兜底链

- 网络错误：标 `verification_status: network_error`，不直接判失败
- 404：标 `verification_status: not_found` 并加入 issues
- 速率限制：等待后重试一次，再标 `citation_check: skipped_rate_limit`

## Codex 限制

- 只读核验；不得修改 `review.md`、`references.bib`、`candidates.csv`、`matrix.csv`
- `verify.json` 顶层必须保留 `overall_status`、`issues`、`run_id`、`checked_at`
