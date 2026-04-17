# Phase 2 — Skills 分离：新增 `claude-code.md` 兄弟文件 + Runtime Router

> 遵循 [`plan/structure.md`](./structure.md) §2 / §3.1。
> 产出：8 个 skill 目录下各新增一个 `claude-code.md`（Claude Code 专属指令），对应 `SKILL.md` 顶部统一加 Runtime Router。**不** 往 SKILL.md 里 "双写"。
> 目标：OpenClaw 继续读 `SKILL.md`（现有语义不变）；Claude Code 读 `SKILL.md + claude-code.md`。两份文件互不侵入。
> 依赖 phase：0。与 phase 1 / 3 并行安全。

## 改造前后对比

### 改造前（当前现状）
```
skills/paper-scout/
├── SKILL.md            # OpenClaw 原生：web_fetch:/exec:/openclaw browser + 所有知识
└── agents/openai.yaml  # OpenClaw 元数据
```
Claude Code 用户要手动翻译。

### 改造后（本 phase 产出）
```
skills/paper-scout/
├── SKILL.md            # 原样保留 OpenClaw 内容；顶部加 Runtime Router 一节
├── claude-code.md      # 新增：Claude Code 专属指令（WebFetch/Bash/Agent/MCP）
└── agents/openai.yaml  # 不动
```
OpenClaw 读 SKILL.md 完全不受影响；Claude Code 读 SKILL.md 的 Runtime Router 跳到 claude-code.md。

### 可选（phase 2.5，非必须）

进一步把 SKILL.md 里 OpenClaw 命令块抽到 `openclaw.md`，SKILL.md 瘦身到共享知识。本 phase **默认不做**，登记到 `plan/STATUS.md` 的"遗留 TODO"。

## 需要改动的 skill 目录（8 个）

| Skill | 是否重 | Claude Code 指令量估计 |
|-------|-------|-----------------------|
| paper-scout | 高 | 大（9 API + 兜底链 + 深挖） |
| paper-analyzer | 中 | 中 |
| review-writer | 低 | 小（主要是写作模板，runtime 无关） |
| verifier | 中 | 中 |
| research-vault | 低 | 小 |
| trendr-watchdog | 中 | 小（与 phase 6 呼应） |
| platform-hotspots | 高 | 大（JS-heavy 平台 + fallback） |
| chrome-cdp-setup | 低 | 小（提示用户启动 CDP 或装 MCP chrome） |

## 改造规范

### 2.1 `SKILL.md` 顶部统一加 Runtime Router

在现有 frontmatter 之后、正文之前插入：

```markdown
## Runtime Router（必读）

识别当前 runtime，只读取对应 sibling，另一方休眠：

- `openclaw`    → 本文件内原有指令块仍然有效（`web_fetch:` / `exec:` / `openclaw browser`）
- `claude-code` → **跳过本文件的指令块**，读 `./claude-code.md` 获取 Claude Code 原生工具调用方式
- `codex` / `cli` → 参考 `./claude-code.md`（命名与 HTTP 工具最接近，必要时进一步降级）

本节之后的章节描述 **共享知识**（源、字段契约、评分规则、故障处理）。指令块保持现状（OpenClaw 语法），Claude Code 读者请切换到 `./claude-code.md`。
```

**不** 改 frontmatter（保留现有 `name` / `description` / `metadata.openclaw`），保持 OpenClaw 解析完全兼容。Claude Code 识别 skill 走 plugin manifest（phase 5），不依赖 SKILL.md frontmatter 额外字段。

### 2.2 `skills/<name>/claude-code.md` 模板

每个文件顶部固定格式：

```markdown
---
runtime: claude-code
parent_skill: <name>
allowed-tools:
  - WebFetch
  - Bash
  - Read
  - Write
  - ...（按需）
---

> 本文件仅在 `claude-code` runtime 下被加载；其它 runtime 读 `./SKILL.md` 的原生指令块。
> 共享知识（源清单、字段契约、评分规则）见同目录 `SKILL.md`。本文件只描述 Claude Code 工具调用方式。

## 使用方法

（本 skill 在 Claude Code 下的工作流，按章节组织）

## 指令映射

（OpenClaw `web_fetch:` / `exec:` / `sessions_spawn` 的等价 Claude Code 工具调用）

## 兜底链

（Claude Code 下的 fallback 策略）

## Claude Code 限制

（没有 MCP chrome 时的降级路径；工具权限；已知问题）
```

### 2.3 OpenClaw ↔ Claude Code 工具映射（适用于所有 skill）

| OpenClaw | Claude Code 等价 | 备注 |
|----------|-----------------|------|
| `web_fetch: { url: ... }` | `WebFetch(url=..., prompt="...")` 工具 | prompt 描述要提取什么 |
| `exec: <cmd>` | `Bash(command=...)` 工具 | 注意 sandbox / 权限 |
| `read <path>` | `Read(file_path=...)` 工具 | |
| `write <path>` | `Write(file_path=..., content=...)` 工具 | |
| `sessions_spawn <agent>` | `Agent(subagent_type=<agent>, prompt=...)` 工具 | |
| `openclaw browser --browser-profile cdp open/evaluate/close` | MCP chrome server（若安装）/ `WebFetch`（静态） / `Bash: curl` 兜底 | 没有 MCP chrome 时显式标 `skipped_with_reason` |
| `supervisor.py` 会话注入 | N/A — Claude Code 由 hooks 接管（phase 6） | |

每个 skill 的 `claude-code.md` 应当引用本表或直接内联对应行。

### 2.4 每个 skill 的 `allowed-tools` 建议

| Skill | allowed-tools |
|-------|---------------|
| paper-scout | WebFetch, WebSearch, Bash, Read, Write, Grep, Glob, Agent |
| paper-analyzer | Read, Write, Bash, WebFetch, Agent |
| review-writer | Read, Write, Bash, Grep |
| verifier | Read, Write, WebFetch, Bash, Grep |
| research-vault | Read, Write, Bash |
| trendr-watchdog | Read, Write, Bash |
| platform-hotspots | WebFetch, WebSearch, Bash, Read, Write, Agent |
| chrome-cdp-setup | Bash, Read |

### 2.5 特殊处理

- `skills/trendr-watchdog/claude-code.md`：正文只写一句"Claude Code 下 watchdog 由 hooks 接管，详见 phase 6 产出的 `runtimes/claude-code/hooks/`。本文件保留占位。"
- `skills/chrome-cdp-setup/claude-code.md`：提示用户优先装 MCP chrome server；若无，用 `WebFetch` 处理静态页面；不要尝试调 OpenClaw CLI。
- `skills/platform-hotspots/claude-code.md`：对每个平台给出优先级链 `MCP chrome > WebFetch > WebSearch > skipped_with_reason`。每个平台对应一小节。

## 步骤（对每个 skill 执行一次）

1. 读取 `skills/<name>/SKILL.md`。
2. 在 frontmatter 下方、现有正文之前插入 `## Runtime Router（必读）` 小节（内容按 2.1 模板）。若已有 "Runtime Router (Mandatory)" 小节，替换文字为 2.1 模板；优先级条目暂保留旧顺序（`OPENCLAW_SESSION_ID` 在前），**不**在本 phase 翻转（phase 8 统一改）。
3. 新建 `skills/<name>/claude-code.md`，按 2.2 模板填写，内容从 SKILL.md 现有指令块 **翻译** 过来（不复制原 OpenClaw 语法）。
4. 对 skill 里的兜底链 / fallback 段：在 `claude-code.md` 里用 Claude Code 工具重写一遍。
5. 冒烟：`python -c "import yaml; yaml.safe_load(open('skills/<name>/claude-code.md').read().split('---')[1])"` 能解析 frontmatter。
6. 不改 SKILL.md 其余内容；不改 `skills/<name>/agents/*.yaml`。

## 验收清单

- [ ] 8 个 skill 目录下都存在 `claude-code.md`。
- [ ] 每份 `claude-code.md` 顶部有 frontmatter（`runtime`, `parent_skill`, `allowed-tools`）。
- [ ] 每份 `SKILL.md` 开头有 `Runtime Router（必读）` 小节，指向 `./claude-code.md`。
- [ ] `git diff --name-only skills/` 只显示 `SKILL.md` 顶部 diff + 8 个新 `claude-code.md`。
- [ ] `python -m pytest tests/test_skill_contracts.py -q` 通过（如果测试没断言新字段，先不改；phase 7 统一加）。
- [ ] OpenClaw 冒烟（若有环境）：跑 `openclaw agent --agent paper-scout --message "hello"`，不报 "skill SKILL.md parse error"。
- [ ] `plan/STATUS.md` phase 2 勾选；遗留 TODO 新增一条：`SKILL.md 彻底分离到 openclaw.md（phase 2.5，可选）`。

## 风险

- R-1（Runtime Router 小节污染 OpenClaw 读取）：小节用标准 `##` 标题 + 纯描述文本，不含 OpenClaw 解析敏感字段。现有 OpenClaw agent 会把它当作普通 guidance 文字读过，无副作用。
- R-2（`claude-code.md` frontmatter 让 OpenClaw 扫描失败）：OpenClaw 只加载 `SKILL.md`；不会主动扫描同目录 `claude-code.md`。仍担心可在 `skills/<name>/claude-code.md` 第一行加注释 `<!-- OpenClaw: ignore -->`。
- R-3（翻译漂移）：SKILL.md 的 OpenClaw 指令更新后，`claude-code.md` 容易忘记同步。phase 7 契约测试加一条：两份文件修改时间差 > 30 天时给 warning（非硬失败）。
- 回滚：`git revert` + 删 `skills/*/claude-code.md` + 回退 SKILL.md Runtime Router 小节。

## 不做的事

- 不拆 OpenClaw 指令到 `openclaw.md`（登记为 phase 2.5 选做）。
- 不改 frontmatter 增加 Claude Code 字段（plugin manifest 接管发现）。
- 不创建 `.claude/` 目录（phase 3/4）。
- 不改 Runtime 优先级（phase 8）。
