"""Tests for ClaudeCodeAdapter (native + subprocess modes)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest import mock

import pytest

from engine.adapters.claude_code import ClaudeCodeAdapter


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_adapter(tmp_path: Path, mode: str = "native") -> ClaudeCodeAdapter:
    return ClaudeCodeAdapter(
        repo_root=tmp_path,
        mode=mode,
        project_dir=tmp_path / "project",
        poll_sec=0.05,
        max_wait_sec=0.5,
    )


def write_completion(adapter: ClaudeCodeAdapter, handle: str, status: str = "completed", output: str = "done") -> None:
    comp_dir = adapter.project_dir / ClaudeCodeAdapter.COMPLETION_DIR
    comp_dir.mkdir(parents=True, exist_ok=True)
    (comp_dir / f"{handle}.json").write_text(
        json.dumps({"handle": handle, "status": status, "output": output}),
        encoding="utf-8",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_platform_name_always_claude_code_native(tmp_path):
    adapter = make_adapter(tmp_path, mode="native")
    assert adapter.platform_name == "claude-code"


def test_platform_name_always_claude_code_subprocess(tmp_path):
    adapter = make_adapter(tmp_path, mode="subprocess")
    assert adapter.platform_name == "claude-code"


def test_native_spawn_agent_writes_dispatch_line(tmp_path):
    adapter = make_adapter(tmp_path)
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)
    handle = adapter.spawn_agent("paper-scout", "find papers on RAG")

    dispatch_path = tmp_path / "project" / ClaudeCodeAdapter.DEFAULT_DISPATCH_FILE
    assert dispatch_path.exists()
    line = json.loads(dispatch_path.read_text().strip())
    assert line["op"] == "agent"
    assert line["agent_id"] == "paper-scout"
    assert line["handle"] == handle
    assert "task" in line


def test_native_await_agent_reads_completion_file(tmp_path):
    adapter = make_adapter(tmp_path)
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)
    handle = adapter.spawn_agent("paper-analyzer", "analyze papers")

    write_completion(adapter, handle, status="completed", output="analysis done")
    result = adapter.await_agent(handle)

    assert result["status"] == "completed"
    assert result["output"] == "analysis done"


def test_native_await_agent_timeout(tmp_path):
    adapter = make_adapter(tmp_path)
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)
    handle = "review-lead_fake_999"

    result = adapter.await_agent(handle)
    assert result["status"] == "timeout"
    assert "error" in result


def test_subprocess_mode_delegates_to_cli_adapter(tmp_path):
    adapter = make_adapter(tmp_path, mode="subprocess")
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)

    with mock.patch(
        "engine.adapters.cli.CLIAdapter.spawn_agent",
        return_value="cli_handle_123",
    ) as mocked:
        handle = adapter.spawn_agent("verifier", "verify review")

    mocked.assert_called_once_with("verifier", "verify review", 900)
    assert handle == "cli_handle_123"


def test_read_write_file_roundtrip(tmp_path):
    for mode in ("native", "subprocess"):
        adapter = make_adapter(tmp_path, mode=mode)
        target = tmp_path / "test_file.txt"
        adapter.write_file(target, "hello world")
        assert adapter.read_file(target) == "hello world"


def test_run_shell_native_returns_instruction_dict(tmp_path):
    adapter = make_adapter(tmp_path, mode="native")
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)

    dispatch_path = tmp_path / "project" / ClaudeCodeAdapter.DEFAULT_DISPATCH_FILE

    def fake_await(handle, poll_sec=10):
        if dispatch_path.exists():
            for line in dispatch_path.read_text().splitlines():
                rec = json.loads(line)
                if rec.get("handle") == handle:
                    return {"status": "completed", "output": "0"}
        return {"status": "timeout"}

    with mock.patch.object(adapter, "await_agent", side_effect=fake_await):
        result = adapter.run_shell("echo hi")

    assert dispatch_path.exists()
    lines = [json.loads(l) for l in dispatch_path.read_text().splitlines() if l.strip()]
    bash_ops = [l for l in lines if l.get("op") == "bash"]
    assert len(bash_ops) == 1
    assert bash_ops[0]["command"] == "echo hi"


def test_send_heartbeat_does_not_print_in_native_mode(tmp_path, capsys):
    adapter = make_adapter(tmp_path, mode="native")
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)
    adapter.send_heartbeat(project, {"agent": "review-lead", "state": "ANALYSIS", "message": "running"})

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (project / "heartbeat.json").exists()


def test_send_heartbeat_writes_valid_json(tmp_path):
    adapter = make_adapter(tmp_path, mode="native")
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)
    state = {"agent": "review-lead", "state": "WRITING", "message": "drafting"}
    adapter.send_heartbeat(project, state)

    data = json.loads((project / "heartbeat.json").read_text())
    assert data["state"] == "WRITING"


def test_get_adapter_selects_native_when_claude_code_env_set(tmp_path, monkeypatch):
    """cli.get_adapter routes to ClaudeCodeAdapter with native mode when CLAUDE_CODE_* env is set."""
    import cli as trendr_cli
    import importlib

    monkeypatch.setenv("CLAUDE_CODE_SESSION", "test-session-123")
    monkeypatch.delenv("TRENDR_CC_MODE", raising=False)

    project = tmp_path / "proj"
    project.mkdir()
    adapter = trendr_cli.get_adapter("claude-code", project_dir=project)

    assert adapter.platform_name == "claude-code"
    assert adapter.mode == "native"


def test_get_adapter_selects_subprocess_without_env(tmp_path, monkeypatch):
    import cli as trendr_cli

    for k in list(os.environ):
        if k.startswith("CLAUDE_CODE_"):
            monkeypatch.delenv(k)
    monkeypatch.delenv("TRENDR_CC_MODE", raising=False)

    project = tmp_path / "proj"
    project.mkdir()
    adapter = trendr_cli.get_adapter("claude-code", project_dir=project)

    assert adapter.platform_name == "claude-code"
    assert adapter.mode == "subprocess"


def test_native_dispatch_rotation(tmp_path):
    adapter = make_adapter(tmp_path, mode="native")
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)

    old_dispatch = project / ClaudeCodeAdapter.DEFAULT_DISPATCH_FILE
    old_dispatch.write_text('{"old": true}\n')

    adapter.init_run()

    assert not old_dispatch.exists()
    rotated = list(project.glob("claude_code_dispatch.*.jsonl"))
    assert len(rotated) == 1
