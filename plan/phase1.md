# Phase 1 — ClaudeCodeAdapter（native + subprocess 双模式）

> 遵循 [`plan/structure.md`](./structure.md) §2（engine/adapters/ 是共享 Python 模块层）。
> 产出：`engine/adapters/claude_code.py`、`cli.py` 路由更新、`tests/test_claude_code_adapter.py`。
> 目标：让 `--platform claude-code` 既能在 Claude Code 外部（subprocess）执行，也能在 Claude Code 内部（native instruction mode）被状态机驱动。
> 依赖 phase：0。

## 背景

目前 `get_adapter("claude-code")` 复用 `CLIAdapter`。该类通过 `_call_claude_cli` 把提示扔给 `claude -p`。这条路径有两个问题：

1. 在 Claude Code 内部运行时，Python 启动子进程 `claude -p`，再由另一个 Claude 实例执行任务——相当于嵌套调用，浪费 token 且 API key 未必可用。
2. OpenClaw adapter 的 "instruction mode"（把工具调用序列化为 JSON，由宿主 agent 执行）在 Claude Code 侧缺失。

Phase 1 新增 `ClaudeCodeAdapter`，显式区分：
- `mode="subprocess"`：外部进程，走现有 `claude -p`（保持现行行为，回归兼容）。
- `mode="native"`：TrendR 运行在 Claude Code 会话里，状态机只写 dispatch 文件与返回占位 handle；真正的工具调用由宿主 Claude Code agent 完成。

## 参考实现（OpenClawAdapter）

`engine/adapters/openclaw.py` 已有 `instruction` vs `cli` 两种 mode。复刻同样模式：
- `spawn_agent` 在 `native` 模式下写 `<project_dir>/claude_code_dispatch.jsonl`（追加一行），等待 `<project_dir>/claude_code_completions/<handle>.json` 出现后再通过 `await_agent` 读取。
- `http_get` / `run_shell` / `browser_eval` 在 `native` 模式返回结构化 instruction dict；state machine 可选择落盘或让 adapter 内部阻塞等待，由宿主 agent "行走" dispatch 文件完成。

## 文件清单

### 新建

1. `engine/adapters/claude_code.py` — 主适配器。
2. `tests/test_claude_code_adapter.py` — 覆盖两种模式的关键路径。
3. `docs/CLAUDE_CODE_ADAPTER.md` — 简要说明两种模式何时使用、dispatch 文件格式。

### 修改

1. `cli.py::get_adapter` — `claude-code` 路由到新适配器。
2. `engine/adapters/__init__.py` — 导出 `ClaudeCodeAdapter`。
3. `cli.py::cmd_run` / `cmd_resume` — 在 `platform == "claude-code"` 时读取 `TRENDR_CC_MODE` 环境变量（`native` / `subprocess`，缺省 `native` 当检测到 `CLAUDE_CODE_*` 环境时，否则 `subprocess`）。
4. `plan/STATUS.md` — 更新 phase 1 状态。

### 不动

- `engine/adapters/cli.py` 保留原样（仍服务 `platform=cli` / `codex`）。它的 `_call_claude_cli` 方法被 `ClaudeCodeAdapter(mode="subprocess")` 复用或软迁移（见 4.3）。

## 详细步骤

### 1.1 `ClaudeCodeAdapter` 契约

```python
class ClaudeCodeAdapter(PlatformAdapter):
    """Adapter for Claude Code runtime (native tool calls or subprocess)."""

    DEFAULT_DISPATCH_FILE = "claude_code_dispatch.jsonl"
    COMPLETION_DIR = "claude_code_completions"

    def __init__(
        self,
        repo_root: Path,
        mode: str = "native",            # "native" | "subprocess"
        project_dir: Optional[Path] = None,
        poll_sec: float = 2.0,
        max_wait_sec: int = 1800,
    ): ...

    @property
    def platform_name(self) -> str:
        return "claude-code"
```

必须实现的抽象方法与行为映射（逐条）：

| 抽象方法 | `native` 模式 | `subprocess` 模式 |
|---------|--------------|------------------|
| `spawn_agent(agent_id, task, timeout_sec)` | 写一行 `{"handle", "op":"agent", "agent_id", "task", "subagent_type", "timeout_sec"}` 到 dispatch 文件，返回 handle | 调用 `CLIAdapter._call_claude_cli` 逻辑（或直接复用 `CLIAdapter`） |
| `await_agent(handle, poll_sec)` | 轮询 `COMPLETION_DIR/<handle>.json`，超时后返回 `{"status": "timeout"}` | 直接查本地缓存（同步完成） |
| `http_get(url, headers)` | 返回 instruction `{"tool":"WebFetch","url":url,"prompt":"return raw body"}`，同时写 dispatch；state machine 若需要同步值，调用 `await_agent(handle)` | 使用 `urllib.request`（复刻 `CLIAdapter.http_get`） |
| `run_shell(cmd, timeout_sec)` | instruction `{"tool":"Bash","command":cmd,"timeout_sec":...}` + dispatch | `subprocess.run(shell=True)` |
| `read_file(path)` | 直接本地读（两种 mode 一致） | 同左 |
| `write_file(path, content)` | 直接本地写（两种 mode 一致） | 同左 |
| `send_heartbeat(project_dir, state)` | 写 `heartbeat.json`，不 print（避免 Claude Code UI 噪音） | 写 `heartbeat.json` + print |
| `browser_eval(js, url)` | instruction `{"tool":"mcp__chrome__evaluate","url":url,"js":js}`（若有 MCP chrome server）或 `{"tool":"Bash","command":"node -e ..."}` 兜底 | 复刻 `CLIAdapter.browser_eval` |

### 1.2 Dispatch 文件格式（native 模式）

- 追加式 JSON Lines，路径：`<project_dir>/claude_code_dispatch.jsonl`。
- 每行一个"待宿主 Claude Code 执行"的工具调用请求。
- 完成后，宿主写结果到 `<project_dir>/claude_code_completions/<handle>.json`，内容：
  ```json
  {
    "handle": "paper-scout_1713350400123",
    "status": "completed",          // completed | failed | timeout
    "output": "...",
    "artifacts": ["candidates.csv", "search_log.md"],
    "error": null,
    "ended_at": "2026-04-17T13:22:00Z"
  }
  ```
- adapter 只负责写 dispatch + 读 completion；具体"让谁去执行 dispatch" 放到 phase 6 的 hooks 里。
- 为避免跨 run 污染：`_init_run()` 时 rename 旧 dispatch 文件为 `claude_code_dispatch.<timestamp>.jsonl`。

### 1.3 同步 vs 异步

- `native` 模式下 `spawn_agent + await_agent` 会阻塞 Python 进程。当 TrendR 作为 Claude Code 内子程序运行时不会有问题，因为宿主 Claude 拉起 Python 前已经完成了自己的 "先 plan 后 exec" 模式。但若 Python 本身就是在 Claude Code 工具上下文中被同步调用，请在 phase 6 hooks 里加入"Python 不阻塞，改写 resume_request.json" 的分支。
- 初版允许阻塞；`max_wait_sec` 给 30 分钟。
- 超时后返回 `{"status":"timeout"}` 并在 state machine 侧按 retry 规则处理。

### 1.4 `cli.py` 路由

```python
def get_adapter(platform: str):
    platform_name = normalize_runtime(platform)
    if platform_name == "openclaw":
        from engine.adapters.openclaw import OpenClawAdapter
        return OpenClawAdapter(mode="cli")
    if platform_name == "claude-code":
        from engine.adapters.claude_code import ClaudeCodeAdapter
        mode = os.environ.get("TRENDR_CC_MODE", "").strip().lower()
        if not mode:
            mode = "native" if any(k.startswith("CLAUDE_CODE_") for k in os.environ) else "subprocess"
        return ClaudeCodeAdapter(
            repo_root=Path(__file__).parent,
            mode=mode,
        )
    if platform_name in {"codex", "cli"}:
        from engine.adapters.cli import CLIAdapter
        return CLIAdapter(repo_root=Path(__file__).parent, platform_name=platform_name)
    ...
```

`cmd_run` / `cmd_resume` 在构造 state machine 前调用 `adapter.project_dir = project_dir`（或 adapter 初始化就接收 project_dir），以便 native 模式找到 dispatch 路径。

### 1.5 迁移 `_call_claude_cli`

- **不删除** `engine/adapters/cli.py::_call_claude_cli` 与 `_try_runtime_native`。
- `ClaudeCodeAdapter(mode="subprocess").spawn_agent` 内部实例化一个 `CLIAdapter(platform_name="claude-code")` 并委派 `spawn_agent`，保留所有 `claude auth status`、超时处理、错误 hint 逻辑。
- 后续某个 phase 如果要彻底合并，再起新 phase 讨论。phase 1 只做"增量 + 委派"。

### 1.6 日志 / 诊断

- adapter 内使用 `logger = logging.getLogger("trendr.adapters.claude_code")`。
- `native` 模式每次 spawn 打印一行 INFO：`dispatched agent=<id> handle=<h> project=<dir>`。
- `subprocess` 模式由底层 `CLIAdapter` 控制输出。
- 不 print 到 stdout，以免污染 Claude Code UI。

## 单元测试（tests/test_claude_code_adapter.py）

必须覆盖：

1. `test_platform_name_always_claude_code` — 两种 mode 都返回 `claude-code`。
2. `test_native_spawn_agent_writes_dispatch_line` — dispatch 文件出现且 JSON 合法。
3. `test_native_await_agent_reads_completion_file` — 预写 completion 文件后 `await_agent` 返回匹配 status。
4. `test_native_await_agent_timeout` — 没写 completion 时超时返回 `{"status":"timeout"}`（用 `max_wait_sec=0.2` 加速）。
5. `test_subprocess_mode_delegates_to_cli_adapter` — 用 `monkeypatch` 替换 `CLIAdapter.spawn_agent`，验证调用参数。
6. `test_read_write_file_roundtrip` — 两种 mode 一致。
7. `test_run_shell_native_returns_instruction` — 没有真实执行，仅返回 instruction dict，并写 dispatch。
8. `test_send_heartbeat_does_not_print_in_native_mode` — capsys 断言 stdout 为空。
9. `test_get_adapter_selects_native_when_claude_code_env_set` — 在 `cli.py::get_adapter` 层面测环境分支（可 monkeypatch `os.environ`）。

测试风格与 `tests/test_openclaw_adapter.py` 对齐（pytest + tmp_path）。

## 验收清单

- [ ] `engine/adapters/claude_code.py` 实现全部抽象方法。
- [ ] `python -m pytest tests/test_claude_code_adapter.py -q` 全绿。
- [ ] `python -m pytest tests/ -q` 全部旧测试通过（OpenClaw/CLI/state_machine 不受影响）。
- [ ] `python cli.py run --topic "smoke" --platform claude-code --project-dir /tmp/trendr-smoke --no-watchdog` 在无 API key 的干净环境里：
  - `native` 模式：生成 dispatch 文件后超时退出（预期行为，打印友好错误）。
  - `subprocess` 模式：因 `claude` CLI 未登录而返回带 hint 的错误，**不崩溃**。
- [ ] `docs/CLAUDE_CODE_ADAPTER.md` 写明 dispatch 格式、两种 mode 选择逻辑、与 phase 6 hooks 的衔接位。
- [ ] `plan/STATUS.md` phase 1 勾选。

## 风险与回滚

- R-1（dispatch 文件与状态机并发读写）：native 模式下 Python 同步写 dispatch 并轮询 completion，不会并发写同一 key；多 agent 通过 handle 区分。单测 4 模拟超时分支。
- R-2（`claude` CLI 在不同 OS 路径不同）：委派给现有 `CLIAdapter._call_claude_cli`，其已用 `shutil.which`。
- R-3（orchestrator 假设 adapter 同步）：state_machine 只调用 `spawn_agent + await_agent`，native 模式下 adapter 阻塞至 completion 文件出现，无需修改 state machine。
- 回滚：`git revert <phase1 commit>` + 删除 `engine/adapters/claude_code.py`、`tests/test_claude_code_adapter.py`、`docs/CLAUDE_CODE_ADAPTER.md`；把 `cli.py::get_adapter` 恢复到旧逻辑。

## 不在本 phase 做的事

- 不修改任何 SKILL.md（phase 2）。
- 不创建 `.claude/` 目录（phase 3/4）。
- 不写 hooks（phase 6）。
- 不改 runtime 优先级（phase 8）。
