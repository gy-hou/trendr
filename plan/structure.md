# 结构约定：分离式布局 + 运行时休眠

> 这是 TrendR "多 runtime 共存" 的 **唯一权威约定**。所有 phase 引用这里的路径与规则。
> 核心原则：母文件夹放共享，运行时专属放各自子文件夹；运行时加载自己的那份，另一方自动休眠。

## 1. 总览

```
trendr/
├── engine/                    # 共享：Python 状态机与 adapter 抽象（runtime-agnostic）
│   └── adapters/
│       ├── base.py            # 共享
│       ├── openclaw.py        # OpenClaw 专属，但放在共享 adapter 层因为是 Python 模块
│       ├── claude_code.py     # Claude Code 专属（phase 1 新增）
│       └── cli.py             # cli/codex 用
│
├── skills/<name>/             # 共享：每个 skill 一个目录
│   ├── SKILL.md               # 共享知识：字段契约、源清单、评分规则、故障处理
│   ├── openclaw.md            # OpenClaw 原 web_fetch:/exec:/openclaw browser 指令（从 SKILL.md 拆出或新建）
│   └── claude-code.md         # Claude Code WebFetch/Bash/Agent/MCP 指令（phase 2 新增）
│
├── agents/<name>/             # 共享：每个 agent 一个目录
│   ├── CONTRACT.md            # 共享：角色、I/O 契约、禁止项、heartbeat 规则（可选，可延后）
│   ├── SOUL.md                # OpenClaw 专属（原文件，不动）
│   └── claude-code.md         # Claude Code subagent 权威源（phase 3 新增）
│
├── runtimes/                  # 运行时专属顶层目录
│   ├── openclaw/
│   │   ├── install.sh         # 从原 install.sh 拆过来的 OpenClaw 分支
│   │   └── uninstall.sh
│   └── claude-code/
│       ├── install.sh         # Claude Code 安装脚本
│       ├── uninstall.sh
│       ├── plugin.json        # Claude Code plugin 清单（权威源）
│       ├── commands/          # slash 命令模板（含 {{repo_root}} 占位符）
│       │   ├── tr.md
│       │   └── tr/*.md
│       ├── hooks/
│       │   ├── session_start.py
│       │   ├── stop_heartbeat.py
│       │   └── subagent_stop.py
│       └── settings.json.example
│
├── install.sh                 # 顶层分派：--openclaw|--claude-code|--all，默认交互菜单
├── uninstall.sh               # 对称
│
├── .claude/                   # ⚠ 安装产物，非权威源。生成自 runtimes/claude-code/*
│   ├── agents/<name>.md       # 由 installer 从 agents/<name>/claude-code.md 拷贝/软链
│   ├── commands/tr.md         # 由 installer 从 runtimes/claude-code/commands/ 渲染
│   └── settings.json.example  # 软链到 runtimes/claude-code/settings.json.example
│
└── .claude-plugin/
    └── plugin.json            # 软链到 runtimes/claude-code/plugin.json（Claude Code 约定路径）
```

## 2. 共享 vs 专属：分界线

| 类别 | 共享位置 | OpenClaw 专属 | Claude Code 专属 |
|------|---------|--------------|-----------------|
| Python 引擎 | `engine/` 全部 | — | — |
| 平台 adapter | — | `engine/adapters/openclaw.py` | `engine/adapters/claude_code.py` |
| Skill 知识 | `skills/<name>/SKILL.md`（源清单、字段、评分） | `skills/<name>/openclaw.md` | `skills/<name>/claude-code.md` |
| Agent 契约 | `agents/<name>/CONTRACT.md`（可选，phase 3 选做） | `agents/<name>/SOUL.md` | `agents/<name>/claude-code.md` |
| 安装脚本 | `install.sh` 顶层分派 | `runtimes/openclaw/install.sh` | `runtimes/claude-code/install.sh` |
| Slash 命令 | — | — | `runtimes/claude-code/commands/` |
| Hooks | — | `skills/trendr-watchdog/supervisor.py` | `runtimes/claude-code/hooks/` |
| Plugin 清单 | — | — | `runtimes/claude-code/plugin.json` |

## 3. 休眠机制：如何在运行时只加载"自己那份"

### 3.1 SKILL.md 顶部统一加 Runtime Router

每个 `skills/<name>/SKILL.md` 开头第一节固定写：

```markdown
## Runtime Router（必读）

识别当前 runtime，读取对应 sibling，另一方 literal 存在但不加载：

- `openclaw`    → 读 `./openclaw.md`（与本文件同目录）
- `claude-code` → 读 `./claude-code.md`
- `codex`/`cli` → 退化到 `./claude-code.md`（HTTP 工具命名最接近）或按文中 fallback

下方章节只写 **runtime-agnostic 知识**（源清单、字段契约、评分规则、故障处理原则）。
任何 runtime 专属命令都 **不** 出现在 SKILL.md 里。
```

### 3.2 Agent 同理

`agents/<name>/` 目录下，SOUL.md 与 claude-code.md 是平级替代。宿主 runtime 各读各的：
- OpenClaw agent registry 指向 `agents/<name>/SOUL.md`（现状）。
- Claude Code subagent 系统指向 `.claude/agents/<name>.md`（installer 生成，内容 = `agents/<name>/claude-code.md`）。
- 共用的内容（输入/输出契约、禁止项）放 `CONTRACT.md`；两边用 `请先阅读 ./CONTRACT.md` 引用。CONTRACT.md 第一版可以是空 stub，后续慢慢抽共享段。

### 3.3 Installer 不跨界

- `runtimes/openclaw/install.sh` 只写 `~/.openclaw/`、只改 OpenClaw 配置、**绝不** 动 `.claude/` 或 `runtimes/claude-code/`。
- `runtimes/claude-code/install.sh` 只写 `.claude/`、`.claude-plugin/`、`~/.claude/` 或 plugin registry，**绝不** 动 `~/.openclaw/`。
- 顶层 `install.sh` 解析 flag 后调子脚本，本身不做安装逻辑。

## 4. 向后兼容保证

- OpenClaw 用户现有的 `skills/<name>/SKILL.md` 路径 **不变**。Phase 2 允许两种过渡策略：
  1. **最小改动（推荐默认）**：SKILL.md 保留现有全部 OpenClaw 内容；另起 `claude-code.md` 写 Claude Code 指令。`openclaw.md` 暂不拆（phase 2 内可选延后）。
  2. **彻底分离（可选，phase 2.5）**：把 SKILL.md 里的 OpenClaw 命令块剪贴到 `openclaw.md`，SKILL.md 只剩共享知识。SOUL.md 加一行 "另读 sibling `openclaw.md`"。
- `agents/<name>/SOUL.md` 路径 **不变**，phase 3 只新增 `claude-code.md` 兄弟。
- `install.sh` 顶层脚本 **不改名**、**不删**；只把内部逻辑抽进 `runtimes/openclaw/install.sh`，顶层变成 dispatcher。旧用户跑 `./install.sh` 仍能触发默认 OpenClaw 流程（交互菜单里默认高亮 OpenClaw，直到 phase 8 再翻转默认）。

## 5. 命名约定

- 目录/文件名用连字符（`claude-code.md`，不是 `claude_code.md` 或 `claudecode.md`）。
- 例外：Python 模块必须 snake_case，所以 `engine/adapters/claude_code.py`。
- Markdown 文件内引用 sibling 用相对路径：`./openclaw.md`、`./claude-code.md`。
- Runtime 标识符永远用 canonical：`openclaw` | `claude-code` | `codex` | `cli`；别名 `claudecode → claude-code` 只在 CLI 入口归一，文件/目录名不用别名。

## 6. 谁来保证"休眠"真的生效

- **SKILL.md 的 Runtime Router** 是第一道防线（告诉 agent 读哪个 sibling）。
- **SOUL.md / `.claude/agents/*.md` 的 frontmatter**：显式 `allowed-tools` 子集，Claude Code 不会拿 OpenClaw 工具，OpenClaw agent registry 不加载 `.claude/agents/*.md`。
- **Installer 分离**：上文 §3.3。
- **Phase 7 契约测试**：断言 OpenClaw 文件集合与 Claude Code 文件集合无交叉（除共享层）。

## 7. 逃生出口：同时启用两边

用户可以 `./install.sh --all` 同时装两个 runtime。共存时：
- 共享文件只有一份，两边都 resolve 到同一个 SKILL.md / CONTRACT.md / `engine/`。
- 专属文件各在各的 `runtimes/<name>/` 下，互不干扰。
- 真正跑起来仍由 `engine/runtime.py::detect_runtime` 在进程级决定当前激活哪一个。

## 8. 如何引用本文档

每个 phase 开头写一句："遵循 `plan/structure.md` §N" 并指向具体章节（例：`§3.1` 指 Runtime Router 格式）。后续所有路径都以本文档为准；本文档更新时所有 phase 自动跟进。
