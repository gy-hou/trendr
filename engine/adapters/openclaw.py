"""OpenClaw platform adapter for TrendR v2.

Maps state machine operations to OpenClaw primitives:
    spawn_agent  → sessions_spawn + sessions_yield
    http_get     → web_fetch
    run_shell    → exec:
    browser_eval → openclaw browser --browser-profile cdp eval "..."
    read_file    → read
    write_file   → write

This adapter generates instructions for the LLM agent running inside OpenClaw.
It does NOT import openclaw directly — it produces command strings that the
OpenClaw runtime interprets.

See ARCHITECTURE.md §2.2 for the full specification.
"""

import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import PlatformAdapter


class OpenClawAdapter(PlatformAdapter):
    """Adapter for running TrendR inside OpenClaw sessions.

    When TrendR runs inside an OpenClaw agent session, the adapter translates
    state machine operations into OpenClaw tool calls. Since OpenClaw tool calls
    are executed by the LLM agent (not by Python directly), this adapter operates
    in two modes:

    1. **Instruction mode** (default): Generates tool-call instruction strings
       that the orchestrating LLM agent should execute. Used when the state machine
       is being interpreted by an LLM agent (e.g., review-lead).

    2. **CLI mode**: Directly executes openclaw CLI commands via subprocess.
       Used when running from cli.py outside an agent session.

    Args:
        mode: "instruction" or "cli"
        browser_profile: Browser profile name for CDP (default: "cdp")
        session_id: OpenClaw session ID (for CLI mode agent injection)
    """

    AGENT_ERROR_MARKERS = (
        "authentication_error",
        "invalid api key",
        "unknown agent id",
        "permission denied",
    )
    def __init__(
        self,
        mode: str = "instruction",
        browser_profile: str = "cdp",
        session_id: Optional[str] = None,
    ):
        self.mode = mode
        self.browser_profile = browser_profile
        self.session_id = session_id
        self._pending_agents: dict[str, dict] = {}  # handle → {agent_id, task, status}

    UNSAFE_SHELL_MARKERS = ("&&", "||", ";", "|", "`", "$(", "<", ">", "\n", "\r")

    @property
    def platform_name(self) -> str:
        return "openclaw"

    @classmethod
    def _extract_payload_text(cls, parsed: Optional[dict]) -> str:
        if not isinstance(parsed, dict):
            return ""

        payloads = parsed.get("result", {}).get("payloads", [])
        texts = [
            payload.get("text", "")
            for payload in payloads
            if isinstance(payload, dict) and payload.get("text")
        ]
        return "\n".join(texts).strip()

    @classmethod
    def _result_stop_reason(cls, parsed: Optional[dict]) -> str:
        if not isinstance(parsed, dict):
            return ""

        result = parsed.get("result", {})
        completion = result.get("completion", {}) if isinstance(result, dict) else {}
        stop_reason = (
            result.get("stopReason")
            or completion.get("stopReason")
            or completion.get("finishReason")
            or ""
        )
        return str(stop_reason).strip().lower()

    @classmethod
    def _looks_like_agent_error(cls, parsed: Optional[dict], output_text: str) -> bool:
        stop_reason = cls._result_stop_reason(parsed)
        if stop_reason in {"error", "failed", "aborted"}:
            return True

        normalized = output_text.strip().lower()
        if not normalized:
            return False

        if any(marker in normalized for marker in cls.AGENT_ERROR_MARKERS):
            return True

        first_line = normalized.splitlines()[0]
        return first_line.startswith("error:") or first_line.startswith("http 4") or first_line.startswith("http 5")

    # ── Agent lifecycle ─────────────────────────────────────────────

    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int = 900) -> str:
        """Dispatch a sub-agent via sessions_spawn.

        In instruction mode, returns a command string.
        In CLI mode, invokes openclaw CLI directly.
        """
        handle = f"{agent_id}_{int(time.time())}"

        if self.mode == "instruction":
            # Generate instruction for the orchestrating LLM
            instruction = {
                "tool": "sessions_spawn",
                "params": {
                    "task": task,
                    "agentId": agent_id,
                    "mode": "run",
                    "runTimeoutSeconds": timeout_sec,
                }
            }
            self._pending_agents[handle] = {
                "agent_id": agent_id,
                "instruction": instruction,
                "status": "pending",
            }
            return handle

        elif self.mode == "cli":
            # Direct CLI execution
            cmd = [
                "openclaw", "agent",
                "--agent", agent_id,
                "--message", task,
                "--timeout", str(timeout_sec),
                "--json",
            ]
            if self.session_id:
                cmd.extend(["--session-id", self.session_id])

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout_sec + 30
                )
                parsed = None
                if result.stdout.strip():
                    try:
                        parsed = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        parsed = None

                payload_text = self._extract_payload_text(parsed)

                summary = parsed.get("summary") if isinstance(parsed, dict) else None
                status = parsed.get("status") if isinstance(parsed, dict) else None
                output_text = payload_text or result.stdout
                looks_like_agent_error = self._looks_like_agent_error(parsed, output_text)
                agent_status = (
                    "completed"
                    if result.returncode == 0 and status == "ok" and not looks_like_agent_error
                    else "failed"
                )
                error_text = result.stderr
                if agent_status != "completed" and not error_text.strip() and looks_like_agent_error:
                    error_text = output_text

                self._pending_agents[handle] = {
                    "agent_id": agent_id,
                    "status": agent_status,
                    "output": output_text,
                    "error": error_text,
                    "summary": summary,
                    "raw": parsed if parsed is not None else result.stdout,
                }
            except subprocess.TimeoutExpired:
                self._pending_agents[handle] = {
                    "agent_id": agent_id,
                    "status": "timeout",
                }
            except FileNotFoundError:
                self._pending_agents[handle] = {
                    "agent_id": agent_id,
                    "status": "failed",
                    "error": "openclaw CLI not found",
                }

            return handle

        raise ValueError(f"Unknown mode: {self.mode}")

    def await_agent(self, handle: str, poll_sec: int = 10) -> dict:
        """Wait for agent completion.

        In instruction mode, returns immediately with the instruction to execute.
        In CLI mode, the result is already available from spawn_agent.
        """
        agent = self._pending_agents.get(handle, {})

        if self.mode == "instruction":
            # In instruction mode, the LLM agent handles yield/poll
            return {
                "status": "completed",
                "instruction": {
                    "tool": "sessions_yield",
                    "note": "Poll until subagent reaches terminal state, then read artifacts",
                },
            }

        return {
            "status": agent.get("status", "unknown"),
            "output": agent.get("output", ""),
            "error": agent.get("error", ""),
            "summary": agent.get("summary"),
            "raw": agent.get("raw"),
        }

    # ── HTTP ────────────────────────────────────────────────────────

    def http_get(self, url: str, headers: Optional[dict] = None) -> dict:
        if self.mode == "instruction":
            return {
                "tool": "web_fetch",
                "params": {"url": url, "headers": headers},
            }

        # CLI mode: use curl
        cmd = ["curl", "-sS", "-L", url]
        if headers:
            for k, v in headers.items():
                cmd.extend(["-H", f"{k}: {v}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "status_code": 200 if result.returncode == 0 else 500,
                "body": result.stdout,
                "headers": {},
            }
        except Exception as e:
            return {"status_code": 0, "body": "", "error": str(e)}

    # ── File I/O ────────────────────────────────────────────────────

    def read_file(self, path: Path) -> str:
        path = Path(path).expanduser().resolve()
        if self.mode == "instruction":
            return json.dumps({"tool": "read", "path": str(path)})
        return path.read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        path = Path(path).expanduser().resolve()
        if self.mode == "instruction":
            # Return instruction; the LLM agent will execute it
            return  # In practice, the state machine writes files directly
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # ── Shell ───────────────────────────────────────────────────────

    def run_shell(self, command: str, timeout_sec: int = 30) -> dict:
        if self.mode == "instruction":
            return {"tool": "exec", "command": command}

        if any(marker in command for marker in self.UNSAFE_SHELL_MARKERS):
            return {
                "exit_code": 2,
                "stdout": "",
                "stderr": "unsafe shell metacharacters are not allowed in OpenClawAdapter CLI mode",
            }

        try:
            argv = shlex.split(command)
        except ValueError as e:
            return {"exit_code": 2, "stdout": "", "stderr": f"invalid shell command: {e}"}

        if not argv:
            return {"exit_code": 2, "stdout": "", "stderr": "empty shell command"}

        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout_sec
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
        """Write heartbeat to file. OpenClaw agents also update progress.md."""
        heartbeat_path = Path(project_dir) / "heartbeat.json"
        heartbeat_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # ── Browser ─────────────────────────────────────────────────────

    def browser_eval(self, js: str, url: Optional[str] = None) -> str:
        if self.mode == "instruction":
            cmd = f"openclaw browser --browser-profile {self.browser_profile}"
            if url:
                cmd += (
                    f" navigate {shlex.quote(url)} && "
                    f"openclaw browser --browser-profile {self.browser_profile}"
                )
            cmd += f" eval {shlex.quote(js)}"
            return json.dumps({"tool": "exec", "command": cmd})

        # CLI mode
        try:
            outputs = []
            if url:
                nav = subprocess.run(
                    ["openclaw", "browser", "--browser-profile", self.browser_profile, "navigate", url],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if nav.returncode != 0:
                    return nav.stderr.strip() or nav.stdout.strip() or "browser navigate failed"
                if nav.stdout:
                    outputs.append(nav.stdout.strip())

            result = subprocess.run(
                ["openclaw", "browser", "--browser-profile", self.browser_profile, "eval", js],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return result.stderr.strip() or result.stdout.strip() or "browser eval failed"
            if result.stdout:
                outputs.append(result.stdout.strip())
            return "\n".join(part for part in outputs if part).strip()
        except Exception as e:
            return f"Error: {e}"
