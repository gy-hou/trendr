# Phase 5 — Installer 分离 + Plugin 清单

> 遵循 [`plan/structure.md`](./structure.md) §1 / §3.3 / §7。
> 产出：
> - `runtimes/openclaw/install.sh` / `uninstall.sh`（从原 `install.sh` / `uninstall.sh` 搬过来）
> - `runtimes/claude-code/install.sh` / `uninstall.sh`（新增）
> - `runtimes/claude-code/plugin.json`（Claude Code plugin 清单权威源）
> - 顶层 `install.sh` / `uninstall.sh` 改为 **dispatcher**（解析 flag 后调子脚本）
> - `.claude-plugin/plugin.json` 作为软链产物指向 `runtimes/claude-code/plugin.json`（由 Claude Code installer 创建）
> 目标：一个 `install.sh` 顶层入口，两个运行时互不污染；用户可 `--claude-code`、`--openclaw` 或 `--all` 任选。
> 依赖 phase：2、3、4、6（manifest 里引用的资源都要存在；phase 6 的 hooks 可留空占位文件）。

## 改造前后对比

### 当前
```
install.sh                # 长脚本，OpenClaw + Skill + Scrapling + Zotero 全塞在里面
uninstall.sh
```

### 改造后
```
install.sh                # 顶层 dispatcher，~100 行
runtimes/
├── openclaw/
│   ├── install.sh        # 原 install.sh 的 OpenClaw 相关主体
│   └── uninstall.sh
└── claude-code/
    ├── install.sh        # 新增
    ├── uninstall.sh      # 新增
    ├── plugin.json       # Claude Code plugin 权威源
    ├── commands/         # phase 4 产物
    ├── hooks/            # phase 6 产物
    └── settings.json.example
```

Claude Code 安装产物（非权威）：
```
.claude/
├── agents/<name>.md      # 软链 → agents/<name>/claude-code.md
├── commands/tr.md        # 渲染自 runtimes/claude-code/commands/
└── commands/tr/*.md
.claude-plugin/
└── plugin.json           # 软链 → runtimes/claude-code/plugin.json
```

## 5.1 顶层 `install.sh`（dispatcher）

新 `install.sh` 只做三件事：
1. 解析 flag：`--openclaw | --claude-code | --all | -h | --help`（无 flag 进交互菜单）。
2. 根据 flag 调 `runtimes/<runtime>/install.sh`。
3. 打印汇总。

模板（伪代码）：

```bash
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mode=""
scope="project"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --openclaw)    mode="openclaw"; shift;;
    --claude-code) mode="claude-code"; shift;;
    --all)         mode="all"; shift;;
    --user)        scope="user"; shift;;
    --project)     scope="project"; shift;;
    --dry-run)     DRY_RUN=1; shift;;
    -h|--help)     cat <<EOF
Usage: ./install.sh [--openclaw|--claude-code|--all] [--user|--project] [--dry-run]
  无 flag：进入交互菜单（默认高亮 openclaw，直到 phase 8 翻转）
EOF
      exit 0;;
    *) echo "Unknown flag: $1" >&2; exit 2;;
  esac
done

if [[ -z "$mode" ]]; then
  # interactive menu: 1) openclaw (default)  2) claude-code  3) all
  ...
fi

export DRY_RUN SCRIPT_DIR scope

case "$mode" in
  openclaw)    bash "$SCRIPT_DIR/runtimes/openclaw/install.sh";;
  claude-code) bash "$SCRIPT_DIR/runtimes/claude-code/install.sh";;
  all)
    bash "$SCRIPT_DIR/runtimes/openclaw/install.sh"
    bash "$SCRIPT_DIR/runtimes/claude-code/install.sh";;
esac
```

## 5.2 `runtimes/openclaw/install.sh`

**做法**：把当前 `install.sh` 里所有 OpenClaw / Skill 注册 / Scrapling / Zotero 相关的主体逻辑整段搬过来，改 `SCRIPT_DIR` 为 `"$(cd "$(dirname "$0")/../.." && pwd)"`（仓库根），不修改业务逻辑。

搬完后原 `install.sh` 里只剩 dispatcher 骨架。诊断用：`diff <(旧 install.sh 主体) <(新 runtimes/openclaw/install.sh 主体)` 必须只有 `SCRIPT_DIR` 类路径相关 diff。

## 5.3 `runtimes/claude-code/install.sh`（新增）

职责：
1. 检测 `claude` CLI 是否在 PATH；否：打印安装提示并 `exit 1`（除非 `--force`）。
2. 校验权威源存在：`agents/*/claude-code.md`（4 个）、`runtimes/claude-code/commands/`、`runtimes/claude-code/plugin.json`、`runtimes/claude-code/hooks/`。
3. 生成 `.claude/agents/<name>.md`：
   - `ln -sf "$SCRIPT_DIR/agents/<name>/claude-code.md" "$target/.claude/agents/<name>.md"`
   - 若用户不允许 symlink，退回 `cp`。
4. 渲染 `.claude/commands/**/*.md`：
   - 调 `runtimes/claude-code/render-commands.sh --dst "$target/.claude/commands" --repo-root "$SCRIPT_DIR"`.
5. 建立 `.claude-plugin/plugin.json` 软链：
   - `ln -sf "$SCRIPT_DIR/runtimes/claude-code/plugin.json" "$target/.claude-plugin/plugin.json"`
6. 若 `--user` scope：把以上 target 切到 `~/.claude/`，并建立 `~/.claude/plugins/trendr/` 软链指向仓库根。
7. 追加 hooks 到 `~/.claude/settings.json`（merge，不覆盖用户其它设置）：
   - 读现有 settings.json（不存在就建 `{}`）。
   - 只 merge 以 `trendr_` 前缀命名的 hook 条目；不覆盖同名字段。
   - 写回。
8. 打印 "TrendR Claude Code install done"，给 `/tr research "topic"` 使用示例。

## 5.4 `runtimes/claude-code/uninstall.sh`（新增）

对称清理：
- 删除 5.3 的 `.claude/agents/*.md` 软链（先验证是 trendr 创建的，不删用户自建的）。
- 删除 `.claude/commands/tr*`。
- 删除 `.claude-plugin/plugin.json` 软链（仅当指向我们时）。
- 删除 `~/.claude/plugins/trendr/`。
- 从 `~/.claude/settings.json` 移除 `trendr_*` hook 条目。
- 打印清理摘要。

**不**删 `runtimes/claude-code/` 本身（那是仓库内容）；**不**碰 OpenClaw 相关目录。

## 5.5 `runtimes/claude-code/plugin.json`（权威源）

```json
{
  "name": "trendr",
  "version": "2.0.0",
  "description": "TrendR — recoverable literature-review harness with platform hotspots",
  "homepage": "https://github.com/<owner>/trendr",
  "author": { "name": "TrendR" },
  "keywords": ["research", "literature-review", "state-machine", "verifier"],

  "agents": [
    "../../agents/paper-scout/claude-code.md",
    "../../agents/paper-analyzer/claude-code.md",
    "../../agents/review-lead/claude-code.md",
    "../../agents/verifier/claude-code.md"
  ],

  "commands": [
    "commands/tr.md",
    "commands/tr/research.md",
    "commands/tr/hotspots.md",
    "commands/tr/status.md",
    "commands/tr/resume.md",
    "commands/tr/template.md"
  ],

  "skills": [
    "../../skills/paper-scout",
    "../../skills/paper-analyzer",
    "../../skills/review-writer",
    "../../skills/verifier",
    "../../skills/research-vault",
    "../../skills/trendr-watchdog",
    "../../skills/platform-hotspots",
    "../../skills/chrome-cdp-setup"
  ],

  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py\"" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/stop_heartbeat.py\"" }] }
    ],
    "SubagentStop": [
      { "hooks": [{ "type": "command", "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/subagent_stop.py\"" }] }
    ]
  }
}
```

路径注意：
- `agents/*` 指向 `agents/<name>/claude-code.md`（权威源）。Claude Code plugin loader 若不支持相对路径 `../../`，installer 5.3-3 的软链方案作为兜底（manifest 不直接引用跨目录）。
- 如果 Claude Code spec 要求 skill 是子目录，`skills/*` 指向仓库的 skill 目录；skill 内部的 Runtime Router 会引导读 `claude-code.md`。

## 5.6 `.claude-plugin/plugin.json` 的处理

Claude Code 惯例路径是仓库根下 `.claude-plugin/plugin.json`。两种实现方式：

- **方式 A（软链）**：`runtimes/claude-code/install.sh` 在仓库根创建软链 `.claude-plugin/plugin.json → runtimes/claude-code/plugin.json`。`.gitignore` 忽略 `.claude-plugin/plugin.json`（避免软链被提交）。
- **方式 B（二次源）**：在仓库根提交一份极短的 `.claude-plugin/plugin.json`，内容只是 `{ "$ref": "../runtimes/claude-code/plugin.json" }`（需 Claude Code 支持 `$ref`；若不支持则走方式 A）。

phase 5 默认方式 A。方式 B 由 phase 8 考虑是否切换。

## 5.7 版本号

- `pyproject.toml` 不改（phase 8 统一升 2.1.0）。
- `plugin.json.version = "2.0.0"`（当前 v2 GA）。
- 顶层 `install.sh` 的 `VERSION` 变量保持不变或与 `pyproject.toml` 同步。

## 步骤

1. 新建 `runtimes/openclaw/` 和 `runtimes/claude-code/` 目录。
2. 把当前 `install.sh` 内容整段拷贝到 `runtimes/openclaw/install.sh`；调整 `SCRIPT_DIR` 为 `"$(cd "$(dirname "$0")/../.." && pwd)"`；确保所有相对路径引用仓库根仍然正确。
3. 把当前 `uninstall.sh` 同法搬到 `runtimes/openclaw/uninstall.sh`。
4. 重写顶层 `install.sh` 为 5.1 的 dispatcher；保留 banner / 版本行。
5. 新建 `runtimes/claude-code/install.sh` / `uninstall.sh` 按 5.3 / 5.4 实现。
6. 新建 `runtimes/claude-code/plugin.json` 按 5.5。
7. 更新 `.gitignore`：
   ```
   .claude-plugin/plugin.json   # by claude-code installer (symlink)
   .claude/commands/             # rendered from runtimes/claude-code/commands/
   ```
   `.claude/agents/` 的处理决策（软链 vs 提交）：本 phase 推荐软链，`.gitignore` 也加 `.claude/agents/`。
8. 本地跑一次 `./install.sh --claude-code --project --dry-run`：打印"将会做以下事情"列表，不做实际改动。
9. 本地跑一次 `./install.sh --openclaw --dry-run`：输出与改造前一致（diff 旧输出）。
10. 更新 `plan/STATUS.md` phase 5。

## 验收

- [ ] `install.sh` 顶层 ~100 行；主体逻辑已搬走。
- [ ] `runtimes/openclaw/install.sh` 行为与原 `install.sh --openclaw-only` 完全一致（diff 原脚本输出）。
- [ ] `runtimes/claude-code/install.sh --dry-run` 列出所有将创建的软链/文件。
- [ ] `runtimes/claude-code/plugin.json` 合法 JSON（`jq .`）。
- [ ] `./install.sh` 无 flag 时进入交互菜单，默认选项 OpenClaw（phase 8 再翻转）。
- [ ] `./install.sh --claude-code --project` 在当前仓库执行后：`.claude/agents/` 有 4 个软链，`.claude/commands/tr*` 渲染成功，`.claude-plugin/plugin.json` 软链到 `runtimes/claude-code/plugin.json`。
- [ ] `./uninstall.sh --claude-code` 清理以上产物且不动 OpenClaw 目录。
- [ ] `plan/STATUS.md` phase 5 勾选。

## 风险

- R-1（脚本搬迁破坏相对路径引用）：搬完立刻用 `--dry-run` 对比旧版输出；如有引用 `./scripts/` 或 `./skills/`，统一改为 `$SCRIPT_DIR/...` 其中 `SCRIPT_DIR` 指向仓库根。
- R-2（软链在 Windows / WSL 不可用）：installer 检测 `uname` 或 `ln -s` 失败时退回 `cp`；在 `.gitignore` 注释里说明。
- R-3（用户的 `~/.claude/settings.json` 已含复杂配置）：merge 逻辑只加 `trendr_` 前缀 hook；冲突时不覆盖并打印警告。
- R-4（Claude Code plugin spec 升级破坏 manifest）：phase 7 契约测试只断言必需字段；可选字段升级由 phase 8 或后续 phase 跟进。
- 回滚：`git revert` + 手工恢复 `install.sh` / `uninstall.sh`。若已经跑过 installer，先 `./uninstall.sh --claude-code` 再 revert。

## 不做的事

- 不写 hooks 本体（phase 6）。manifest 引用 `hooks/*.py` 即可；文件不存在时 Claude Code 会跳过 hook。
- 不翻转 runtime 优先级 / 默认菜单（phase 8）。
- 不改业务 Python 代码。
