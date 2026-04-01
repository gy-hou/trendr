"""Standalone CLI adapter for TrendR v2.

This adapter runs without OpenClaw by talking directly to the Anthropic API,
using local filesystem I/O, subprocess-based shell execution, and a simple
in-memory handle store for synchronous "agent" execution.
"""

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .base import PlatformAdapter


class CLIAdapter(PlatformAdapter):
    """Platform adapter for standalone CLI execution."""

    ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
        self._results: dict[str, dict] = {}

    @property
    def platform_name(self) -> str:
        return "cli"

    # ── Agent lifecycle ─────────────────────────────────────────────

    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int = 900) -> str:
        """Synchronously execute an agent task via Anthropic Messages API."""
        handle = f"{agent_id}_{int(time.time() * 1000)}"
        soul = self._load_soul(agent_id)
        result = self._call_anthropic(agent_id, soul, task, timeout_sec)
        self._results[handle] = result
        return handle

    def await_agent(self, handle: str, poll_sec: int = 10) -> dict:
        """Return the result already produced by spawn_agent()."""
        return self._results.get(
            handle,
            {"status": "failed", "output": "", "error": f"Unknown handle: {handle}"},
        )

    def _load_soul(self, agent_id: str) -> str:
        soul_path = self.repo_root / "agents" / agent_id / "SOUL.md"
        if not soul_path.exists():
            raise RuntimeError(f"SOUL.md not found for agent '{agent_id}': {soul_path}")
        return soul_path.read_text(encoding="utf-8")

    def _call_anthropic(self, agent_id: str, soul: str, task: str, timeout_sec: int) -> dict:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required for CLIAdapter.spawn_agent(). "
                "Set the environment variable before using platform=cli."
            )

        model = os.environ.get("TRENDR_MODEL", self.DEFAULT_MODEL)
        payload = {
            "model": model,
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "system": soul,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Agent ID: {agent_id}\n\n"
                        f"Task:\n{task}"
                    ),
                }
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.ANTHROPIC_MESSAGES_URL,
            data=body,
            method="POST",
            headers={
                "x-api-key": api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
        )

        previous_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout_sec)
            with urllib.request.urlopen(request) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = ""
            return {
                "status": "failed",
                "output": "",
                "error": f"Anthropic API HTTP {exc.code}: {error_body or exc.reason}",
                "status_code": exc.code,
            }
        except urllib.error.URLError as exc:
            return {
                "status": "failed",
                "output": "",
                "error": f"Anthropic API request failed: {exc.reason}",
            }
        finally:
            socket.setdefaulttimeout(previous_timeout)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "output": "",
                "error": "Anthropic API returned invalid JSON",
                "raw_response": raw,
            }

        content_blocks = data.get("content", [])
        text_output = "\n".join(
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()

        return {
            "status": "completed",
            "output": text_output,
            "id": data.get("id"),
            "model": data.get("model", model),
            "stop_reason": data.get("stop_reason"),
            "usage": data.get("usage", {}),
            "raw_response": data,
        }

    # ── HTTP ────────────────────────────────────────────────────────

    def http_get(self, url: str, headers: Optional[dict] = None) -> dict:
        request = urllib.request.Request(url, headers=headers or {}, method="GET")
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
                return {
                    "status_code": response.getcode(),
                    "body": body,
                    "headers": dict(response.headers.items()),
                }
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            return {
                "status_code": exc.code,
                "body": body,
                "headers": dict(getattr(exc, "headers", {}).items()) if getattr(exc, "headers", None) else {},
                "error": exc.reason,
            }
        except Exception as exc:
            return {"status_code": 0, "body": "", "headers": {}, "error": str(exc)}

    # ── File I/O ────────────────────────────────────────────────────

    def read_file(self, path: Path) -> str:
        return Path(path).expanduser().resolve().read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    # ── Shell ───────────────────────────────────────────────────────

    def run_shell(self, command: str, timeout_sec: int = 30) -> dict:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
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
        heartbeat_path = Path(project_dir).expanduser().resolve() / "heartbeat.json"
        heartbeat_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(
            f"[heartbeat] {state.get('state', '?')} "
            f"agent={state.get('agent', '?')} "
            f"message={state.get('message', '')}"
        )

    # ── Browser ─────────────────────────────────────────────────────

    def browser_eval(self, js: str, url: Optional[str] = None) -> str:
        script = js
        if url:
            script = f"const TRENDR_URL = {json.dumps(url)};\n{js}"

        try:
            result = subprocess.run(
                ["node", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return "browser not available"
            return result.stdout.strip()
        except Exception:
            return "browser not available"
