---
runtime: claude-code
parent_skill: research-vault
allowed-tools:
  - Read
  - Write
  - Bash
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md` 的原生指令块。
> 共享知识（Vault 结构、索引格式、每日日志模板）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

将研究成果持久化到 Obsidian vault：

1. `Bash(command='echo "$HOME/Documents/Obsidian-Vault"')` 确认 Vault 路径（或从 env `OBSIDIAN_VAULT` 读取）
2. `Bash(command="mkdir -p [VAULT]/Research/{_index,papers,reviews,daily,templates}")` 初始化目录结构
3. 写论文卡片、综述归档、每日日志（见 `SKILL.md` §模板）

## 指令映射

| OpenClaw 原语 | Claude Code 等价 |
|--------------|----------------|
| `exec: VAULT="$HOME/Documents/OpenClaw-Vault"` | `Bash(command='export VAULT="$HOME/Documents/Obsidian-Vault"')` 或直接使用 `OBSIDIAN_VAULT` env |
| `exec: mkdir -p "$VAULT/Research/..."` | `Bash(command="mkdir -p [VAULT_PATH]/Research/...")` |
| `exec: grep -i "[KEYWORD]" "$VAULT/..."` | `Grep(pattern="[KEYWORD]", path="[VAULT_PATH]/Research/")` |
| `write: [VAULT]/...` | `Write(file_path="[VAULT_PATH]/...", content=...)` |
| `read: [VAULT]/...` | `Read(file_path="[VAULT_PATH]/...")` |

## Vault 路径约定

- Claude Code runtime 使用 `OBSIDIAN_VAULT` env（若设置）或默认 `~/Documents/Obsidian-Vault`
- OpenClaw runtime 使用 `~/Documents/OpenClaw-Vault`
- 两者可指向同一物理 vault，通过 env 覆盖

## 兜底链

- obsidian-cli 不可用 → 直接用 `Write` 写 Markdown 文件到 vault 路径，功能等价
- Vault 路径不存在 → `Bash(command="mkdir -p [VAULT_PATH]/Research")` 初始化

## Claude Code 限制

- 不使用 `obsidian-cli` CLI（非标准工具）；直接文件操作等价。
- 论文池索引 CSV 可用 `Grep` 快速检索，不需要完整加载。
