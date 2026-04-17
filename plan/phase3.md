# Phase 3 — Agents 分离：`agents/<name>/claude-code.md` 兄弟文件

> 遵循 [`plan/structure.md`](./structure.md) §2 / §3.2。
> 产出：4 个 agent 目录下各新增一个 `claude-code.md`（权威源），可选新增 `CONTRACT.md`（共享契约）。不动 SOUL.md。
> 目标：Claude Code 下的 subagent 定义与 OpenClaw SOUL 分离，两份平级替代；`.claude/agents/<name>.md` 在 phase 5 由 installer 从 `agents/<name>/claude-code.md` 生成/软链。
> 依赖 phase：0。与 phase 1 / 2 并行安全。

## 改造前后对比

### 当前
```
agents/paper-scout/
└── SOUL.md            # OpenClaw 专用
```

### 本 phase 产出
```
agents/paper-scout/
├── SOUL.md            # 不动
├── claude-code.md     # 新增：Claude Code subagent 权威源
└── CONTRACT.md        # 新增（可选）：shared I/O 契约，两份兄弟都 reference 它
```

Claude Code 安装时（phase 5 installer）会软链 `.claude/agents/paper-scout.md → agents/paper-scout/claude-code.md`，让 Claude Code subagent 系统能识别。

## 4 个 agent（与现有目录一致）

| agent | 权威源 | 模型建议 |
|-------|--------|---------|
| paper-scout | `agents/paper-scout/claude-code.md` | sonnet |
| paper-analyzer | `agents/paper-analyzer/claude-code.md` | sonnet |
| review-lead | `agents/review-lead/claude-code.md` | opus（协调 + 写作）|
| verifier | `agents/verifier/claude-code.md` | sonnet |

## `agents/<name>/claude-code.md` 规范

### 3.1 Frontmatter（Claude Code subagent 格式）

```yaml
---
name: paper-scout
description: "Search and score academic papers across 9 sources. Use proactively during TrendR DISCOVERY or when the user requests a literature scan."
tools: WebFetch, WebSearch, Bash, Read, Write, Grep, Glob
model: sonnet
runtime: claude-code
parent_agent: paper-scout
---
```

- `name`：与目录名一致。
- `description`：Claude Code 按此选 agent，写 "Use proactively when …" 风格。
- `tools`：逗号分隔，**子集关系** — 必须 ⊆ 对应 skill 的 `allowed-tools`（phase 2 决定）。
- `model`：4 个 agent 默认 `sonnet`；review-lead 用 `opus`。
- `runtime` / `parent_agent`：TrendR 自定义字段，不影响 Claude Code 原生解析，用于契约测试。

### 3.2 Body 结构（7 段固定格式）

```markdown
> 本文件是 `claude-code` runtime 下 `<name>` subagent 的权威源。
> OpenClaw 用户请读 `./SOUL.md`。共享契约见 `./CONTRACT.md`（若存在）。

## 1. 角色（Role）
<一句话描述 agent 身份与目标>

## 2. 运行时提示（Runtime）
你运行在 Claude Code 内。禁止使用 OpenClaw 原语（`web_fetch:` / `exec:` / `sessions_spawn`）。
所有工具调用都通过 frontmatter 声明的 Claude Code 原生工具完成。

## 3. 输入契约（Input）
- `project_dir`: 绝对路径
- `topic` / `depth` / <其他必需字段>

## 4. 输出契约（Output）
在 `project_dir` 下写 <具体文件清单>，字段/header 严格对齐：<引用 skill SKILL.md §output schema>

## 5. 工作流（Tool Usage）
1. 先读 `skills/<related>/SKILL.md`（共享知识）与 `skills/<related>/claude-code.md`（Claude Code 指令）。
2. <按阶段列步骤>
3. 每完成一个子步骤写一次 heartbeat：`project_dir/heartbeat.json`

## 6. 故障处理（Failure）
<网络 block / rate limit / 工具不可用时的退路>

## 7. 禁止（Forbidden）
- 编造论文/引用/字段。
- 使用 OpenClaw 原语。
- 不写 heartbeat 或跳过产物落盘。
- 提前宣告"已完成"而未产出承诺文件。
```

### 3.3 每 agent 要点差异

- **paper-scout**：
  - 工具集覆盖 9 个 API 源 + 兜底链；读 `skills/paper-scout/claude-code.md`。
  - 输出 `candidates.csv` + `search_log.md`；0 结果也要写 header。
- **paper-analyzer**：
  - 读 `skills/paper-analyzer/claude-code.md`；输出 `notes/<paper_id>.md` + `matrix.csv`。
  - 每篇论文按模板填字段。
- **review-lead**：
  - **opus** 模型；协调三个子 agent + 自己写综述。
  - 禁止提前声明完成；VERIFY 由 verifier agent 判定。
  - 读 `skills/review-writer/claude-code.md` + `skills/trendr-watchdog/claude-code.md`。
- **verifier**：
  - 读 `skills/verifier/claude-code.md`；输出 `verify.json`（schema 在 skill 里定义）。
  - 4 类检查：citation existence / claim support / taxonomy coherence / BibTeX 质量。

## `CONTRACT.md`（可选，默认做最小版）

第一版可以只写：

```markdown
# Shared Agent Contract

## Forbidden
- 编造事实：论文 id、引用、字段值。
- 未经用户同意执行 destructive shell 操作（rm -rf、drop table 等）。
- 产出不落盘就结束。

## Heartbeat
文件：`<project_dir>/heartbeat.json`，每 ≤5 分钟或每完成一个子步骤各写一次：
`{"agent":"<id>","state":"<SM state>","message":"<what I just did>","updated_at":"<ISO>"}`

## File I/O
- 写文件前 `mkdir -p` 父目录。
- 原子写：先写 `path.tmp`，再 `os.replace` 到目标路径。
- 不要覆盖用户手工编辑过的文件（若检测到 mtime 超过本 run start，写到 `<path>.new` 并提示）。
```

`SOUL.md` 和 `claude-code.md` 都在首段引用 "请先读 `./CONTRACT.md`"，但**不要** 在本 phase 改 SOUL.md —— 加引用是 phase 3.5（选做，可合并到 phase 2.5）。

## 步骤

1. 对 4 个 agent 各执行：
   a. 读 `agents/<name>/SOUL.md` 吸收原有语义。
   b. 新建 `agents/<name>/claude-code.md` 按 3.1 + 3.2 填写。
   c. `tools` 字段只列该 agent 实际用到的，不复制 skill 全表。
2. 新建 `agents/CONTRACT.md.template`（供后续每个 agent 目录下 CONTRACT.md 复用）。实际在 4 个 agent 目录下生成 `CONTRACT.md` 作为第一版（都是同一内容；后续可差异化）。
3. 冒烟：
   - `python -c "import yaml,pathlib;[yaml.safe_load(p.read_text().split('---')[1]) for p in pathlib.Path('agents').rglob('claude-code.md')]"`
   - 检查 `tools` 字段每项在 Claude Code 合法工具白名单内。
4. 更新 `plan/STATUS.md` phase 3；遗留 TODO 新增：`SOUL.md 引用 CONTRACT.md 的同步改造（phase 3.5，可选）`。

## 验收

- [ ] 4 个 `agents/<name>/claude-code.md` 存在，frontmatter 完整。
- [ ] 4 个 `agents/<name>/CONTRACT.md` 存在（第一版最小内容）。
- [ ] `tools` 字段 ⊆ 对应 skill 的 `allowed-tools`（phase 2 决定）。用脚本对照 `skills/<name>/claude-code.md` frontmatter。
- [ ] `agents/*/SOUL.md` 未被修改（`git diff agents/*/SOUL.md` 为空）。
- [ ] `plan/STATUS.md` phase 3 勾选。

## 风险

- R-1（`.claude/agents/` 软链的方向和权限）：phase 5 installer 统一处理；phase 3 只保证权威源格式正确。
- R-2（tools 过宽 / 过窄）：过窄导致 agent 运行缺工具；过宽降低权限收益。phase 7 e2e 能暴露问题，届时调整。
- R-3（SOUL.md 与 claude-code.md 漂移）：契约测试在 phase 7 加 mtime diff 告警（同 phase 2 R-3）。
- 回滚：`git revert` + 删 `agents/*/claude-code.md` 与 `agents/*/CONTRACT.md`。SOUL.md 没动，OpenClaw 零影响。

## 不做的事

- 不动 `agents/*/SOUL.md`。
- 不创建 `.claude/agents/`（phase 5 installer 负责）。
- 不写 plugin 清单（phase 5）。
- 不引入 hooks（phase 6）。
