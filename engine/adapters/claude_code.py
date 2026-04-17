"""Claude Code platform adapter for TrendR v2.

Maps state machine operations to Claude Code primitives:
    spawn_agent  → dispatch to claude_code_dispatch.jsonl (native)
                   or delegate to CLIAdapter (subprocess)
    http_get     → WebFetch instruction (native) / urllib (subprocess)
    run_shell    → Bash instruction (native) / subprocess (subprocess)
    browser_eval → mcp__chrome__evaluate instruction (native) / fallback
    read_file    → direct filesystem read (both modes)
    write_file   → direct filesystem write (both modes)

Two operating modes:
  native     — TrendR runs inside a Claude Code session. The adapter writes
               dispatch requests to claude_code_dispatch.jsonl and polls
               claude_code_completions/<handle>.json for results. The
               hosting Claude Code agent is responsible for satisfying ops.
  subprocess — TrendR runs outside Claude Code. The adapter delegates to
               CLIAdapter which calls `claude -p` via subprocess.

See docs/CLAUDE_CODE_ADAPTER.md for dispatch file format details.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base import PlatformAdapter

logger = logging.getLogger("trendr.adapters.claude_code")


class ClaudeCodeAdapter(PlatformAdapter):
    """Adapter for running TrendR with Claude Code as the host runtime.

    Args:
        repo_root: Path to the TrendR repository root.
        mode: "native" or "subprocess".
        project_dir: Research project directory (required for native mode dispatch).
        poll_sec: Polling interval when awaiting completion files.
        max_wait_sec: Maximum seconds to wait before returning timeout.
    """

    DEFAULT_DISPATCH_FILE = "claude_code_dispatch.jsonl"
    COMPLETION_DIR = "claude_code_completions"

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        mode: str = "native",
        project_dir: Optional[Path] = None,
        poll_sec: float = 2.0,
        max_wait_sec: int = 1800,
    ):
        self.repo_root = Path(
            repo_root or Path(__file__).resolve().parents[2]
        ).expanduser().resolve()
        self.mode = mode.lower().strip() if mode else "native"
        self._project_dir: Optional[Path] = Path(project_dir).expanduser().resolve() if project_dir else None
        self.poll_sec = poll_sec
        self.max_wait_sec = max_wait_sec
        self._subprocess_delegate: Optional[object] = None

    @property
    def platform_name(self) -> str:
        return "claude-code"

    @property
    def project_dir(self) -> Optional[Path]:
        return self._project_dir

    @project_dir.setter
    def project_dir(self, value: Path) -> None:
        self._project_dir = Path(value).expanduser().resolve()

    def _get_cli_delegate(self):
        if self._subprocess_delegate is None:
            from .cli import CLIAdapter
            self._subprocess_delegate = CLIAdapter(
                repo_root=self.repo_root,
                platform_name="claude-code",
            )
        return self._subprocess_delegate

    def _require_project_dir(self) -> Path:
        if self._project_dir is None:
            raise RuntimeError(
                "project_dir must be set on ClaudeCodeAdapter before using native mode. "
                "Pass it to __init__ or set adapter.project_dir = <path>."
            )
        return self._project_dir

    def _dispatch_path(self) -> Path:
        return self._require_project_dir() / self.DEFAULT_DISPATCH_FILE

    def _completion_dir(self) -> Path:
        d = self._require_project_dir() / self.COMPLETION_DIR
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _completion_path(self, handle: str) -> Path:
        return self._completion_dir() / f"{handle}.json"

    def _write_dispatch(self, record: dict) -> None:
        """Atomically append one JSON line to the dispatch file."""
        line = json.dumps(record, ensure_ascii=False) + "\n"
        path = self._dispatch_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

    def _rotate_dispatch(self) -> None:
        """Rename existing dispatch file to avoid cross-run pollution."""
        path = self._dispatch_path()
        if path.exists():
            ts = int(time.time())
            path.rename(path.parent / f"claude_code_dispatch.{ts}.jsonl")

    def init_run(self) -> None:
        """Call before starting a new run to rotate stale dispatch files."""
        if self.mode == "native":
            self._rotate_dispatch()

    # ── Agent lifecycle ─────────────────────────────────────────────

    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int = 900) -> str:
        handle = f"{agent_id}_{int(time.time() * 1000)}"

        if self.mode == "native":
            record = {
                "handle": handle,
                "op": "agent",
                "agent_id": agent_id,
                "subagent_type": agent_id,
                "task": task,
                "timeout_sec": timeout_sec,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._write_dispatch(record)
            logger.info("dispatched agent=%s handle=%s project=%s", agent_id, handle, self._project_dir)
            return handle

        return self._get_cli_delegate().spawn_agent(agent_id, task, timeout_sec)

    def await_agent(self, handle: str, poll_sec: int = 10) -> dict:
        if self.mode != "native":
            return self._get_cli_delegate().await_agent(handle, poll_sec)

        comp_path = self._completion_path(handle)
        deadline = time.monotonic() + self.max_wait_sec
        interval = self.poll_sec

        while time.monotonic() < deadline:
            if comp_path.exists():
                try:
                    data = json.loads(comp_path.read_text(encoding="utf-8"))
                    return {
                        "status": data.get("status", "completed"),
                        "output": data.get("output", ""),
                        "artifacts": data.get("artifacts", []),
                        "error": data.get("error"),
                        "ended_at": data.get("ended_at"),
                    }
                except (json.JSONDecodeError, OSError):
                    pass
            time.sleep(interval)

        logger.warning("await_agent timeout handle=%s after %ss", handle, self.max_wait_sec)
        return {"status": "timeout", "output": "", "error": f"No completion after {self.max_wait_sec}s"}

    # ── HTTP ────────────────────────────────────────────────────────

    def http_get(self, url: str, headers: Optional[dict] = None) -> dict:
        if self.mode == "native":
            handle = f"webfetch_{int(time.time() * 1000)}"
            record = {
                "handle": handle,
                "op": "webfetch",
                "url": url,
                "headers": headers or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._write_dispatch(record)
            result = self.await_agent(handle)
            return {
                "status_code": 200 if result.get("status") == "completed" else 0,
                "body": result.get("output", ""),
                "headers": {},
            }

        # subprocess mode: use urllib
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {
                    "status_code": resp.status,
                    "body": resp.read().decode("utf-8", errors="replace"),
                    "headers": dict(resp.headers),
                }
        except urllib.error.HTTPError as e:
            return {"status_code": e.code, "body": e.read().decode("utf-8", errors="replace"), "headers": {}}
        except Exception as e:
            return {"status_code": 0, "body": "", "error": str(e)}

    # ── File I/O ────────────────────────────────────────────────────

    def read_file(self, path: Path) -> str:
        return Path(path).expanduser().resolve().read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.parent / (p.name + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, p)

    # ── Shell ───────────────────────────────────────────────────────

    def run_shell(self, command: str, timeout_sec: int = 30) -> dict:
        if self.mode == "native":
            handle = f"bash_{int(time.time() * 1000)}"
            record = {
                "handle": handle,
                "op": "bash",
                "command": command,
                "timeout_sec": timeout_sec,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._write_dispatch(record)
            result = self.await_agent(handle)
            return {
                "exit_code": 0 if result.get("status") == "completed" else 1,
                "stdout": result.get("output", ""),
                "stderr": result.get("error", "") or "",
            }

        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout_sec
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "timeout"}

    # ── Heartbeat ───────────────────────────────────────────────────

    def send_heartbeat(self, project_dir: Path, state: dict) -> None:
        """Write heartbeat.json without printing to stdout (avoids Claude Code UI noise)."""
        heartbeat_path = Path(project_dir) / "heartbeat.json"
        tmp = heartbeat_path.parent / "heartbeat.json.tmp"
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, heartbeat_path)

    # ── Browser ─────────────────────────────────────────────────────

    def browser_eval(self, js: str, url: Optional[str] = None) -> str:
        if self.mode == "native":
            handle = f"browser_{int(time.time() * 1000)}"
            record = {
                "handle": handle,
                "op": "browser_eval",
                "tool": "mcp__chrome__evaluate",
                "url": url,
                "js": js,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._write_dispatch(record)
            result = self.await_agent(handle)
            return result.get("output", "")

        # subprocess fallback: try node, else return placeholder
        import subprocess
        import shutil
        if not shutil.which("node"):
            return "browser_eval not available in subprocess mode without node"
        try:
            script = f"({js})"
            result = subprocess.run(
                ["node", "-e", f"console.log(JSON.stringify(eval({json.dumps(script)})))"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"
