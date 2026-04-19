---
runtime: codex
parent_skill: research-vault
allowed-tools:
  - exec_command
  - update_plan
---

> 本文件仅在 `codex` runtime 下被加载；`claude-code` 读 `./claude-code.md`，`openclaw` 读 `./SKILL.md`。
> 共享知识（Vault 结构、索引格式、每日日志模板）见同目录 `SKILL.md`。本文件只描述 Codex 工具调用方式。

## 使用方法

将研究成果持久化到 Obsidian vault：

1. 用 `OBSIDIAN_VAULT` 或默认 `~/Documents/Obsidian-Vault`
2. `exec_command(cmd="mkdir -p [VAULT]/Research/{_index,papers,reviews,daily,templates}")`
3. 写论文卡片、综述归档、每日日志

## 指令映射

| OpenClaw 原语 | Codex 等价 |
|--------------|-----------|
| `exec: VAULT=...` | `exec_command(cmd='printf %s \"$OBSIDIAN_VAULT\"')` 或直接使用默认路径 |
| `exec: mkdir -p "$VAULT/Research/..."` | `exec_command(cmd="mkdir -p [VAULT_PATH]/Research/...")` |
| `exec: grep -i ...` | `exec_command(cmd="rg -n --ignore-case ... [VAULT_PATH]/Research")` |
| `write: [VAULT]/...` | 用现有脚本或 `exec_command` 原子写入 Markdown |

## 兜底链

- `obsidian-cli` 不可用：直接文件写入
- Vault 路径不存在：先初始化目录，再写入

## Codex 限制

- Vault 同步本质上是文件操作；不要把它当成在线 API。
- 只写目标文档，不改动无关索引。
