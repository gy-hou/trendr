"""Standalone adapter for non-OpenClaw runtimes.

This adapter supports:
- platform=cli
- platform=codex
- platform=claude-code

It runs with local filesystem I/O + subprocess shell execution and uses
LLM provider APIs (OpenAI or Anthropic) for agent task execution.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from ..runtime import normalize_runtime
from .base import PlatformAdapter


class CLIAdapter(PlatformAdapter):
    """Platform adapter for standalone CLI/Codex/Claude Code execution."""

    ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, repo_root: Optional[Path] = None, platform_name: str = "cli"):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
        self._results: dict[str, dict] = {}
        self._platform_name = normalize_runtime(platform_name)

    @property
    def platform_name(self) -> str:
        return self._platform_name

    # ── Agent lifecycle ─────────────────────────────────────────────

    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int = 900) -> str:
        """Synchronously execute an agent task via configured provider API."""
        handle = f"{agent_id}_{int(time.time() * 1000)}"
        soul = self._load_soul(agent_id)
        result = self._call_model(agent_id, soul, task, timeout_sec)
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

    def _resolve_provider(self) -> str:
        """Resolve provider from env with required fallback behavior."""
        provider = (os.environ.get("TRENDR_PROVIDER", "auto") or "auto").strip().lower()
        if provider not in {"auto", "openai", "anthropic"}:
            raise RuntimeError(
                "Invalid TRENDR_PROVIDER. Use one of: auto | openai | anthropic."
            )

        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if provider == "openai":
            if not openai_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is required when TRENDR_PROVIDER=openai."
                )
            return "openai"

        if provider == "anthropic":
            if not anthropic_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is required when TRENDR_PROVIDER=anthropic."
                )
            return "anthropic"

        # auto mode: OpenAI first, then Anthropic
        if openai_key:
            return "openai"
        if anthropic_key:
            return "anthropic"
        raise RuntimeError(
            "No model API key found. Set OPENAI_API_KEY (preferred) or "
            "ANTHROPIC_API_KEY, or choose TRENDR_PROVIDER explicitly."
        )

    def _call_model(self, agent_id: str, soul: str, task: str, timeout_sec: int) -> dict:
        native_result, native_reason = self._try_runtime_native(agent_id, soul, task, timeout_sec)
        if native_result is not None:
            return native_result

        try:
            provider = self._resolve_provider()
        except RuntimeError as exc:
            if native_reason:
                raise RuntimeError(
                    f"{native_reason} To enable API-key fallback, set OPENAI_API_KEY "
                    f"or ANTHROPIC_API_KEY. ({exc})"
                ) from exc
            raise

        if provider == "openai":
            return self._call_openai(agent_id, soul, task, timeout_sec)
        return self._call_anthropic(agent_id, soul, task, timeout_sec)

    def _try_runtime_native(
        self, agent_id: str, soul: str, task: str, timeout_sec: int
    ) -> tuple[Optional[dict], Optional[str]]:
        """Try runtime-native authenticated CLI path before API keys."""
        if self._platform_name == "codex":
            return self._call_codex_cli(agent_id, soul, task, timeout_sec)
        if self._platform_name == "claude-code":
            return self._call_claude_cli(agent_id, soul, task, timeout_sec)
        return None, None

    def _build_agent_prompt(self, agent_id: str, soul: str, task: str) -> str:
        return (
            f"You are TrendR agent '{agent_id}'.\n\n"
            f"System prompt (must follow):\n{soul}\n\n"
            f"Task:\n{task}\n"
        )

    def _call_codex_cli(
        self, agent_id: str, soul: str, task: str, timeout_sec: int
    ) -> tuple[Optional[dict], Optional[str]]:
        if shutil.which("codex") is None:
            return None, "codex runtime selected, but `codex` CLI is not available."

        prompt = self._build_agent_prompt(agent_id, soul, task)
        model = os.environ.get("TRENDR_MODEL", "").strip()

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        temp_path = temp_file.name
        temp_file.close()
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(self.repo_root),
            "--output-last-message",
            temp_path,
        ]
        if model:
            cmd.extend(["-m", model])
        cmd.append(prompt)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return None, f"codex exec timed out after {timeout_sec}s."
        except Exception as exc:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return None, f"codex exec failed to start: {exc}"

        try:
            output = Path(temp_path).read_text(encoding="utf-8").strip()
        except Exception:
            output = ""
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        if proc.returncode != 0:
            detail = ((proc.stderr or "") or (proc.stdout or "")).strip()
            detail = self._summarize_cli_error(detail)
            hint = ""
            lowered = detail.lower()
            if (
                "not logged in" in lowered
                or "missing bearer" in lowered
                or "unauthorized" in lowered
            ):
                hint = " Authenticate with `codex login`, or set OPENAI_API_KEY for fallback."
            elif "403" in lowered:
                hint = " Check Codex auth/session or org policy."
            return None, f"codex exec failed (exit {proc.returncode}): {detail}{hint}"

        text = output or (proc.stdout or "").strip()
        if not text:
            return None, "codex exec returned empty output."

        return (
            {
                "status": "completed",
                "output": text,
                "provider": "codex-cli",
                "model": model or "runtime-default",
                "raw_response": {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                },
            },
            None,
        )

    def _summarize_cli_error(self, detail: str) -> str:
        if not detail:
            return "unknown error"

        lines = [line.strip() for line in detail.splitlines() if line.strip()]
        if not lines:
            return "unknown error"

        keywords = (
            "error",
            "failed",
            "fail",
            "unauthorized",
            "forbidden",
            "not logged",
            "timeout",
            "timed out",
            "status",
        )
        important = [line for line in lines if any(key in line.lower() for key in keywords)]
        selected = important[-3:] if important else lines[-3:]
        summary = " | ".join(selected)
        return summary[:600]

    def _call_claude_cli(
        self, agent_id: str, soul: str, task: str, timeout_sec: int
    ) -> tuple[Optional[dict], Optional[str]]:
        if shutil.which("claude") is None:
            return None, "claude-code runtime selected, but `claude` CLI is not available."

        try:
            status = subprocess.run(
                ["claude", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as exc:
            return None, f"Failed to check `claude auth status`: {exc}"

        if status.returncode != 0:
            detail = ((status.stderr or "") or (status.stdout or "")).strip()
            return None, f"claude-code runtime selected, but auth status check failed: {detail}"

        logged_in = False
        try:
            payload = json.loads(status.stdout or "{}")
            logged_in = bool(payload.get("loggedIn"))
        except json.JSONDecodeError:
            logged_in = False

        if not logged_in:
            return None, "claude-code runtime selected, but Claude CLI is not logged in. Run `claude auth login`."

        prompt = self._build_agent_prompt(agent_id, soul, task)
        model = os.environ.get("TRENDR_MODEL", "").strip()
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "text",
            "--permission-mode",
            "bypassPermissions",
        ]
        if model:
            cmd.extend(["--model", model])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return None, f"claude -p timed out after {timeout_sec}s."
        except Exception as exc:
            return None, f"claude -p failed to start: {exc}"

        if proc.returncode != 0:
            detail = ((proc.stderr or "") or (proc.stdout or "")).strip()
            detail = detail[:600] if detail else "unknown error"
            return None, f"claude -p failed (exit {proc.returncode}): {detail}"

        text = (proc.stdout or "").strip()
        if not text:
            return None, "claude -p returned empty output."

        return (
            {
                "status": "completed",
                "output": text,
                "provider": "claude-cli",
                "model": model or "runtime-default",
                "raw_response": {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                },
            },
            None,
        )

    def _call_anthropic(self, agent_id: str, soul: str, task: str, timeout_sec: int) -> dict:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required for Anthropic provider."
            )

        model = os.environ.get("TRENDR_MODEL", self.DEFAULT_ANTHROPIC_MODEL)
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

        raw = self._request_with_timeout(request, timeout_sec)
        if "error" in raw:
            return raw

        data = raw["data"]
        content_blocks = data.get("content", [])
        text_output = "\n".join(
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()

        return {
            "status": "completed",
            "output": text_output,
            "provider": "anthropic",
            "id": data.get("id"),
            "model": data.get("model", model),
            "stop_reason": data.get("stop_reason"),
            "usage": data.get("usage", {}),
            "raw_response": data,
        }

    def _call_openai(self, agent_id: str, soul: str, task: str, timeout_sec: int) -> dict:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for OpenAI provider."
            )

        model = os.environ.get("TRENDR_MODEL", self.DEFAULT_OPENAI_MODEL)
        base_url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": soul},
                {
                    "role": "user",
                    "content": (
                        f"Agent ID: {agent_id}\n\n"
                        f"Task:\n{task}"
                    ),
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        raw = self._request_with_timeout(request, timeout_sec)
        if "error" in raw:
            return raw

        data = raw["data"]
        text_output = self._extract_openai_text(data)

        return {
            "status": "completed",
            "output": text_output,
            "provider": "openai",
            "id": data.get("id"),
            "model": data.get("model", model),
            "stop_reason": data.get("choices", [{}])[0].get("finish_reason"),
            "usage": data.get("usage", {}),
            "raw_response": data,
        }

    def _request_with_timeout(self, request: urllib.request.Request, timeout_sec: int) -> dict:
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
                "error": f"HTTP {exc.code}: {error_body or exc.reason}",
                "status_code": exc.code,
            }
        except urllib.error.URLError as exc:
            return {
                "status": "failed",
                "output": "",
                "error": f"API request failed: {exc.reason}",
            }
        finally:
            socket.setdefaulttimeout(previous_timeout)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "output": "",
                "error": "Provider API returned invalid JSON",
                "raw_response": raw,
            }

        return {"data": data}

    def _extract_openai_text(self, data: dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif isinstance(item.get("output_text"), str):
                        parts.append(item["output_text"])
            return "\n".join(p.strip() for p in parts if p and p.strip())
        return ""

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
