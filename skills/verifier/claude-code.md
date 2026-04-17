---
runtime: claude-code
parent_skill: verifier
allowed-tools:
  - Read
  - Write
  - WebFetch
  - Bash
  - Grep
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md` 的原生指令块。
> 共享知识（验证维度、评分规则、verify.json schema）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

Verifier 是只读检查器，不修改任何研究文件，只输出 `verify.json`：

1. 读取全部输入文件（见下方）
2. 按 `SKILL.md` §验证清单 执行各维度检查
3. 对每条引用用 `WebFetch` 验证真实性（可选，有速率限制时可跳过）
4. `Write` 结果到 `~/research/[PROJECT]/verify.json`

## 指令映射

| OpenClaw 原语 | Claude Code 等价 |
|--------------|----------------|
| `read: ~/research/[PROJECT]/review.md` | `Read(file_path="~/research/[PROJECT]/review.md")` |
| `read: ~/research/[PROJECT]/references.bib` | `Read(file_path="~/research/[PROJECT]/references.bib")` |
| `read: ~/research/[PROJECT]/candidates.csv` | `Read(file_path="~/research/[PROJECT]/candidates.csv")` |
| `read: ~/research/[PROJECT]/matrix.csv` | `Read(file_path="~/research/[PROJECT]/matrix.csv")` |
| `web_fetch: { url: "https://arxiv.org/abs/[ID]" }` | `WebFetch(url="https://arxiv.org/abs/[ID]", prompt="确认论文存在，返回标题和摘要")` |
| `write: ~/research/[PROJECT]/verify.json` | `Write(file_path="~/research/[PROJECT]/verify.json", content=...)` |

## 兜底链

- `WebFetch` 验证引用失败（网络错误）→ 标注 `verification_status: "network_error"`，不视为失败
- 引用不可达（404）→ 标注 `verification_status: "not_found"`，降低 citation_score
- 速率受限时 → 跳过在线验证，标注 `citation_check: "skipped_rate_limit"`

## Claude Code 限制

- `Grep` 可用于在 `review.md` 中快速定位引用位置。
- 验证是只读操作；禁止在 verifier 阶段修改 `review.md` 或 `references.bib`。
- `verify.json` 的 schema 见 `SKILL.md` §输出格式；`overall_status` 必须是 `passed` / `failed` / `partial`。
