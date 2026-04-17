"""Tests for runtimes/claude-code/hooks/ — stdin→stdout contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parents[1] / "runtimes" / "claude-code" / "hooks"
SESSION_START = HOOKS_DIR / "session_start.py"
STOP_HEARTBEAT = HOOKS_DIR / "stop_heartbeat.py"
SUBAGENT_STOP = HOOKS_DIR / "subagent_stop.py"


def _run_hook(script: Path, stdin_payload: dict | None, env: dict | None = None) -> tuple[int, dict]:
    """Run a hook script, return (returncode, parsed_stdout_json)."""
    input_bytes = json.dumps(stdin_payload).encode() if stdin_payload is not None else b""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        [sys.executable, str(script)],
        input=input_bytes,
        capture_output=True,
        env=merged_env,
        timeout=10,
    )
    stdout = result.stdout.strip()
    parsed = json.loads(stdout) if stdout else {}
    return result.returncode, parsed


# ---------------------------------------------------------------------------
# session_start.py
# ---------------------------------------------------------------------------


class TestSessionStart:
    def test_exits_zero_with_empty_stdin(self):
        result = subprocess.run(
            [sys.executable, str(SESSION_START)],
            input=b"",
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_empty_stdin_outputs_valid_json(self):
        rc, parsed = _run_hook(SESSION_START, None)
        assert rc == 0
        assert isinstance(parsed, dict)

    def test_no_pending_runs_returns_empty_dict(self, tmp_path):
        env = {"TRENDR_PROJECT_DIR": "", "HOME": str(tmp_path)}
        rc, parsed = _run_hook(SESSION_START, {}, env=env)
        assert rc == 0
        assert parsed == {}

    def test_pending_run_returns_additional_context(self, tmp_path):
        research = tmp_path / "research" / "my-project"
        research.mkdir(parents=True)
        state = {
            "status": "paused",
            "current_state": "ANALYSIS",
            "run_id": "r1",
            "topic": "agentic rag",
            "updated_at": "2026-04-17T10:00:00+00:00",
        }
        (research / "run_state.json").write_text(json.dumps(state), encoding="utf-8")

        env = {"HOME": str(tmp_path)}
        rc, parsed = _run_hook(SESSION_START, {}, env=env)
        assert rc == 0
        output = parsed.get("hookSpecificOutput", {})
        assert output.get("hookEventName") == "SessionStart"
        ctx = output.get("additionalContext", "")
        assert "my-project" in ctx
        assert "ANALYSIS" in ctx

    def test_completed_run_not_included(self, tmp_path):
        research = tmp_path / "research" / "done-project"
        research.mkdir(parents=True)
        state = {
            "status": "completed",
            "current_state": "DONE",
            "run_id": "r2",
            "updated_at": "2026-04-17T09:00:00+00:00",
        }
        (research / "run_state.json").write_text(json.dumps(state), encoding="utf-8")

        env = {"HOME": str(tmp_path)}
        rc, parsed = _run_hook(SESSION_START, {}, env=env)
        assert rc == 0
        assert parsed == {}


# ---------------------------------------------------------------------------
# stop_heartbeat.py
# ---------------------------------------------------------------------------


class TestStopHeartbeat:
    def test_exits_zero(self):
        rc, _ = _run_hook(STOP_HEARTBEAT, {})
        assert rc == 0

    def test_stop_hook_active_skips_write(self, tmp_path):
        project = tmp_path / "research" / "proj"
        project.mkdir(parents=True)
        run_state = {"status": "running", "current_state": "ANALYSIS"}
        (project / "run_state.json").write_text(json.dumps(run_state))

        env = {"TRENDR_PROJECT_DIR": str(project), "HOME": str(tmp_path)}
        rc, _ = _run_hook(STOP_HEARTBEAT, {"stop_hook_active": True}, env=env)
        assert rc == 0
        assert not (project / "heartbeat.json").exists()

    def test_writes_heartbeat_json_when_project_dir_set(self, tmp_path):
        project = tmp_path / "research" / "proj"
        project.mkdir(parents=True)
        run_state = {"status": "running", "current_state": "WRITING"}
        (project / "run_state.json").write_text(json.dumps(run_state))

        env = {"TRENDR_PROJECT_DIR": str(project), "HOME": str(tmp_path)}
        rc, _ = _run_hook(STOP_HEARTBEAT, {}, env=env)
        assert rc == 0

        hb_path = project / "heartbeat.json"
        assert hb_path.exists()
        hb = json.loads(hb_path.read_text())
        assert hb["agent"] == "claude-code-session"
        assert hb["state"] == "WRITING"
        assert hb["message"] == "claude stopped"
        assert "stopped_at" in hb

    def test_no_project_dir_exits_cleanly(self, tmp_path):
        env = {"TRENDR_PROJECT_DIR": "", "HOME": str(tmp_path)}
        rc, _ = _run_hook(STOP_HEARTBEAT, {}, env=env)
        assert rc == 0

    def test_detects_project_via_recent_mtime(self, tmp_path):
        project = tmp_path / "research" / "auto-detect"
        project.mkdir(parents=True)
        run_state = {"status": "running", "current_state": "DISCOVERY"}
        state_file = project / "run_state.json"
        state_file.write_text(json.dumps(run_state))
        # mtime is fresh by default (just written)

        env = {"TRENDR_PROJECT_DIR": "", "HOME": str(tmp_path)}
        rc, _ = _run_hook(STOP_HEARTBEAT, {}, env=env)
        assert rc == 0
        assert (project / "heartbeat.json").exists()


# ---------------------------------------------------------------------------
# subagent_stop.py
# ---------------------------------------------------------------------------


class TestSubagentStop:
    def test_exits_zero_for_unknown_agent(self):
        rc, _ = _run_hook(SUBAGENT_STOP, {"subagent_type": "random-agent", "final_message": "done"})
        assert rc == 0

    def test_exits_zero_for_known_agent_no_project(self, tmp_path):
        env = {"TRENDR_PROJECT_DIR": "", "HOME": str(tmp_path)}
        rc, _ = _run_hook(
            SUBAGENT_STOP,
            {"subagent_type": "paper-scout", "final_message": "found 5 papers"},
            env=env,
        )
        assert rc == 0

    def test_writes_completion_for_known_agent_with_dispatch(self, tmp_path):
        project = tmp_path / "research" / "proj"
        project.mkdir(parents=True)
        (project / "run_state.json").write_text(json.dumps({"status": "running", "current_state": "DISCOVERY"}))

        handle = "scout_abc123"
        dispatch_line = json.dumps({"op": "agent", "handle": handle, "agent_id": "paper-scout"})
        (project / "claude_code_dispatch.jsonl").write_text(dispatch_line + "\n")

        env = {"TRENDR_PROJECT_DIR": str(project), "HOME": str(tmp_path)}
        rc, _ = _run_hook(
            SUBAGENT_STOP,
            {"subagent_type": "paper-scout", "final_message": "found 5 papers"},
            env=env,
        )
        assert rc == 0

        comp_file = project / "claude_code_completions" / f"{handle}.json"
        assert comp_file.exists()
        comp = json.loads(comp_file.read_text())
        assert comp["handle"] == handle
        assert comp["status"] == "completed"
        assert comp["output"] == "found 5 papers"
        assert "ended_at" in comp

    def test_fallback_handle_when_no_dispatch(self, tmp_path):
        project = tmp_path / "research" / "proj"
        project.mkdir(parents=True)
        (project / "run_state.json").write_text(json.dumps({"status": "running", "current_state": "ANALYSIS"}))
        # no dispatch file

        env = {"TRENDR_PROJECT_DIR": str(project), "HOME": str(tmp_path)}
        rc, _ = _run_hook(
            SUBAGENT_STOP,
            {"subagent_type": "verifier", "final_message": "verified"},
            env=env,
        )
        assert rc == 0
        comp_files = list((project / "claude_code_completions").glob("verifier_auto_*.json"))
        assert len(comp_files) == 1
        comp = json.loads(comp_files[0].read_text())
        assert comp["status"] == "completed"
        assert comp["output"] == "verified"

    def test_does_not_overwrite_existing_completion(self, tmp_path):
        project = tmp_path / "research" / "proj"
        (project / "claude_code_completions").mkdir(parents=True)
        (project / "run_state.json").write_text(json.dumps({"status": "running"}))

        handle = "scout_xyz"
        dispatch_line = json.dumps({"op": "agent", "handle": handle, "agent_id": "paper-scout"})
        (project / "claude_code_dispatch.jsonl").write_text(dispatch_line + "\n")

        comp_file = project / "claude_code_completions" / f"{handle}.json"
        original = {"handle": handle, "status": "completed", "output": "original", "artifacts": []}
        comp_file.write_text(json.dumps(original))

        env = {"TRENDR_PROJECT_DIR": str(project), "HOME": str(tmp_path)}
        rc, _ = _run_hook(
            SUBAGENT_STOP,
            {"subagent_type": "paper-scout", "final_message": "new output"},
            env=env,
        )
        assert rc == 0
        # file should not be overwritten
        result = json.loads(comp_file.read_text())
        assert result["output"] == "original"

    @pytest.mark.parametrize("agent", ["paper-scout", "paper-analyzer", "review-lead", "verifier"])
    def test_all_trendr_agents_recognized(self, tmp_path, agent):
        project = tmp_path / "research" / "proj"
        project.mkdir(parents=True)
        (project / "run_state.json").write_text(json.dumps({"status": "running"}))

        env = {"TRENDR_PROJECT_DIR": str(project), "HOME": str(tmp_path)}
        rc, _ = _run_hook(
            SUBAGENT_STOP,
            {"subagent_type": agent, "final_message": "done"},
            env=env,
        )
        assert rc == 0
        comp_files = list((project / "claude_code_completions").glob("*.json"))
        assert len(comp_files) == 1
