# Phase 7 — 测试矩阵 + CI

> 遵循 [`plan/structure.md`](./structure.md) §6（谁保证休眠真生效）。
> 产出：新增/扩展的 pytest 文件、契约校验、端到端冒烟；确保 OpenClaw 能力不回退；**断言两个 runtime 的文件集合无交叉**。
> 目标：phase 1-6 的所有改动都被覆盖；CI 对 `claude-code` 通道与 `openclaw` 通道分别跑一遍。
> 依赖 phase：1-6。

## 测试分层

### 7.1 单元测试（已有 + 新增）

| 文件 | 来源 | 覆盖内容 |
|------|------|---------|
| `tests/test_openclaw_adapter.py` | 已有 | 保持原样，确认未被 phase 1 改动影响 |
| `tests/test_cli_adapter.py` | 已有 | 保持 `_call_claude_cli` / `_call_codex_cli` 逻辑可用 |
| `tests/test_claude_code_adapter.py` | phase 1 新增 | native + subprocess 两种 mode 全路径 |
| `tests/test_state_machine.py` | 已有 | 保持绿 |
| `tests/test_validators.py` | 已有 | 保持 |
| `tests/test_verifier.py` | 已有 | 保持 |
| `tests/test_watchdog.py` | 已有 | 保持；若 phase 6 改了 watchdog 入口，同步更新 |
| `tests/test_hooks.py` | phase 6 新增 | hook 脚本契约 |
| `tests/test_skill_contracts.py` | 已有 → 扩展 | 新增 Claude Code frontmatter 字段断言 |
| `tests/test_hotspots_runner.py` | 已有 | 保持 |
| `tests/test_research_history.py` | 已有 | 保持 |

### 7.2 新增契约测试

#### `tests/test_claude_code_skill_contracts.py`

- 遍历 `skills/*/SKILL.md`，断言 **顶部含 "Runtime Router（必读）" 小节**，且内容指向 `./claude-code.md`。
- 遍历 `skills/*/claude-code.md`（phase 2 新增）：
  - frontmatter 有 `runtime: claude-code`、`parent_skill`、`allowed-tools`。
  - `allowed-tools` 每项在白名单内（`WebFetch, WebSearch, Bash, Read, Write, Grep, Glob, Agent, Edit, Skill, NotebookEdit` 等）。
- 遍历 `agents/*/claude-code.md`（phase 3 新增）：
  - frontmatter 有 `name, description, tools, model, runtime: claude-code, parent_agent`。
  - `tools` 是对应 `skills/<related>/claude-code.md` `allowed-tools` 的子集（可配 name-to-skill 映射表）。
- 遍历 `runtimes/claude-code/commands/**/*.md`：
  - frontmatter 有 `description`、`argument-hint`、`allowed-tools`。
  - body 含 `$ARGUMENTS` 或 `$1` 变量。
  - body 中的 `{{repo_root}}` 出现次数 ≥ 1（除 help 入口 `tr.md` 可为 0）。

#### `tests/test_plugin_manifest.py`

- 解析 `runtimes/claude-code/plugin.json`（权威源）：
  - JSON schema 必需字段（name/version/description）齐全。
  - `agents` / `commands` / `skills` 列表里每个路径**基于 manifest 所在目录**解析后存在。
  - `hooks.*[0].hooks[0].command` 字符串引用 `runtimes/claude-code/hooks/*.py` 真实文件。
- 若 `.claude-plugin/plugin.json` 存在：
  - 断言它是软链（readlink）或与 `runtimes/claude-code/plugin.json` 内容一致。

#### `tests/test_runtime_isolation.py`（新增，专门验证休眠）

断言文件集合互不侵入：

```python
OPENCLAW_EXCLUSIVE = {
    "skills/*/openclaw.md",             # 若 phase 2.5 做了才存在
    "runtimes/openclaw/**",
    "agents/*/SOUL.md",
    "skills/trendr-watchdog/supervisor.py",
}
CLAUDE_CODE_EXCLUSIVE = {
    "skills/*/claude-code.md",
    "agents/*/claude-code.md",
    "runtimes/claude-code/**",
    ".claude/**",
    ".claude-plugin/**",
}
SHARED = {
    "engine/**", "cli.py", "skills/*/SKILL.md",
    "agents/*/CONTRACT.md", "install.sh", "uninstall.sh",
    "tests/**", "docs/**", "plan/**",
}
# 断言：所有跟踪文件属于且仅属于三类之一（正则 / glob 匹配）。
```

- 断言 OpenClaw installer 不引用 Claude Code 路径：grep `runtimes/openclaw/install.sh`，不得出现 `.claude/`、`claude-code.md`、`runtimes/claude-code/`。
- 断言 Claude Code installer 不引用 OpenClaw 路径：grep `runtimes/claude-code/install.sh`，不得出现 `~/.openclaw`、`openclaw ` CLI 调用、`supervisor.py`。

### 7.3 端到端冒烟

新增 `tests/e2e/test_claude_code_smoke.py`（用 pytest marker `@pytest.mark.e2e` 并默认 skip，除非 env `RUN_E2E=1`）：

1. 创建临时 project_dir。
2. 通过 subprocess 启动 `python cli.py run --topic "smoke test" --platform claude-code --project-dir <dir> --depth A --no-watchdog --time-budget 1`。
3. 主进程同时启动一个后台协程，扮演"Claude Code 宿主"：
   - 轮询 `<dir>/claude_code_dispatch.jsonl`
   - 对每个 op 写 fake completion（agent 返回 `candidates.csv` 预制内容；webfetch 返回 200 + 空 body）
4. 等待 CLI 退出，断言 `run_state.json` 存在、`heartbeat.json` 有终态、CLI 退出码为 0 或 1（根据是否人为让 verify 失败）。

这条 e2e 把 phase 1 的 native mode、phase 6 的 hook 协议粘合起来，确保整个 dispatch-completion loop 正确。

### 7.4 回归

- 每次 CI 都跑 OpenClaw 单测；若 CI 上没有 `openclaw` CLI，用 `mode="instruction"` 路径覆盖，不真正调用 CLI。
- `python cli.py run --help` 与 `python cli.py hotspots --help` 的输出快照对比（`tests/test_cli_help_snapshot.py`，snapshot 文件放 `tests/snapshots/`）。

## CI 配置

仓库目前没看到 `.github/workflows/`；phase 7 创建：

`.github/workflows/ci.yml`：

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  pytest:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e .
      - run: python -m pytest tests/ -q --maxfail=5

  smoke-claude-code:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - name: Run native-mode smoke
        env:
          RUN_E2E: "1"
        run: python -m pytest tests/e2e/test_claude_code_smoke.py -q
```

> 若仓库已启用某个 CI 平台（比如 GitHub Actions matrix）但本 phase 跑时未看到 workflow，先在 `plan/STATUS.md` 记"`ci.yml` 是否已存在待确认"，优先走本地 `pytest` 门槛。

## 步骤

1. 先跑一次 `python -m pytest tests/ -q` 建立基线（记录 pass/fail）。
2. 扩展 `tests/test_skill_contracts.py`（增加 "Runtime Router 存在性" 断言）。
3. 新建 `tests/test_claude_code_skill_contracts.py`、`tests/test_plugin_manifest.py`、`tests/test_runtime_isolation.py`、`tests/e2e/test_claude_code_smoke.py`。
4. 新建 `tests/snapshots/` + `tests/test_cli_help_snapshot.py`。
5. 若 `.github/workflows/ci.yml` 不存在，新建；若存在，在原有基础上追加 `smoke-claude-code` job。
6. 运行一次完整测试：`python -m pytest tests/ -q`（不含 e2e，除非显式 `RUN_E2E=1`）。
7. 更新 `plan/STATUS.md` phase 7。

## 验收

- [ ] `python -m pytest tests/ -q` 全绿（允许 skip e2e）。
- [ ] `RUN_E2E=1 python -m pytest tests/e2e -q` 在本地成功。
- [ ] 新增契约测试覆盖 phase 2-6 所有产物。
- [ ] `.github/workflows/ci.yml` 存在且两个 job 能跑通。
- [ ] `plan/STATUS.md` phase 7 勾选。

## 风险

- R-1（e2e flaky）：用 tmpdir + fixed timeout；dispatch poller 做 30s cap。
- R-2（契约测试过严）：仅断言"存在+子集+类型"；不断言具体 body 文案。
- R-3（CI 没装 `claude` CLI）：subprocess 模式的测试用 monkeypatch 跳过真实 `shutil.which`。
- 回滚：`git revert` + 删测试文件；不会影响业务代码。

## 不在本 phase 做的事

- 不改业务代码（phase 1-6 已覆盖）。
- 不改 runtime 优先级（phase 8）。
