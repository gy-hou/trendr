#!/usr/bin/env python3
"""Claude Code SubagentStop hook for TrendR.

When a TrendR subagent (paper-scout, paper-analyzer, review-lead, verifier)
finishes, writes claude_code_completions/<handle>.json to unblock the
ClaudeCodeAdapter's await_agent() polling loop.

Protocol: reads JSON from stdin, exits 0 always.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_LOG = Path.home() / ".trendr" / "hooks.log"
TRENDR_AGENTS = frozenset({"paper-scout", "paper-analyzer", "review-lead", "verifier"})


def _log(event: str, summary: str) -> None:
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(f"{ts} {event} {summary}\n")
    except Exception:
        pass


def _detect_project_dir() -> Path | None:
    env_dir = os.environ.get("TRENDR_PROJECT_DIR", "").strip()
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if (p / "run_state.json").exists():
            return p

    research_root = Path.home() / "research"
    if not research_root.exists():
        return None

    threshold = time.time() - 300
    candidates = []
    for state_file in research_root.glob("*/run_state.json"):
        try:
            if state_file.stat().st_mtime > threshold:
                candidates.append(state_file)
        except OSError:
            continue

    if not candidates:
        return None

    return max(candidates, key=lambda f: f.stat().st_mtime).parent


def _find_pending_handle(dispatch_file: Path, agent_id: str) -> str | None:
    """Find the earliest un-completed dispatch line for this agent_id."""
    if not dispatch_file.exists():
        return None

    try:
        lines = dispatch_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("agent_id") != agent_id and record.get("subagent_type") != agent_id:
            continue
        if record.get("op") != "agent":
            continue
        handle = record.get("handle")
        if not handle:
            continue
        return handle

    return None


def _write_completion(comp_dir: Path, handle: str, output: str) -> None:
    comp_dir.mkdir(parents=True, exist_ok=True)
    comp_path = comp_dir / f"{handle}.json"
    if comp_path.exists():
        return  # already written by a previous hook invocation

    payload = {
        "handle": handle,
        "status": "completed",
        "output": output,
        "artifacts": [],
        "ended_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    tmp = comp_dir / f"{handle}.json.tmp"
    try:
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, comp_path)
    except Exception as exc:
        _log("SubagentStop", f"write completion failed for {handle}: {exc}")


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    subagent_type = payload.get("subagent_type", "")
    final_message = payload.get("final_message", "") or ""

    if subagent_type not in TRENDR_AGENTS:
        sys.exit(0)

    try:
        project_dir = _detect_project_dir()
        if project_dir is None:
            _log("SubagentStop", f"no active project_dir for agent={subagent_type}")
            sys.exit(0)

        dispatch_file = project_dir / "claude_code_dispatch.jsonl"
        comp_dir = project_dir / "claude_code_completions"

        handle = _find_pending_handle(dispatch_file, subagent_type)
        if handle is None:
            # Fallback: generate an auto-detected handle
            handle = f"{subagent_type}_auto_{int(time.time() * 1000)}"
            _log("SubagentStop", f"no dispatch line found for {subagent_type}, using fallback handle={handle}")

        _write_completion(comp_dir, handle, final_message)
        _log("SubagentStop", f"wrote completion handle={handle} agent={subagent_type}")

    except Exception as exc:
        _log("SubagentStop", f"error: {exc}")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
