#!/usr/bin/env python3
"""Claude Code Stop hook for TrendR.

When Claude Code stops a session, writes a terminal heartbeat.json so that
the next SessionStart can detect the interrupted run and offer to resume.

Protocol: reads JSON from stdin, exits 0 always.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_LOG = Path.home() / ".trendr" / "hooks.log"


def _log(event: str, summary: str) -> None:
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(f"{ts} {event} {summary}\n")
    except Exception:
        pass


def _detect_project_dir() -> Path | None:
    # Priority 1: explicit env var
    env_dir = os.environ.get("TRENDR_PROJECT_DIR", "").strip()
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if (p / "run_state.json").exists():
            return p

    # Priority 2: most recently modified run_state.json within last 5 minutes
    research_root = Path.home() / "research"
    if not research_root.exists():
        return None

    threshold = time.time() - 300  # 5 minutes
    candidates = []
    for state_file in research_root.glob("*/run_state.json"):
        try:
            if state_file.stat().st_mtime > threshold:
                candidates.append(state_file)
        except OSError:
            continue

    if not candidates:
        return None

    newest = max(candidates, key=lambda f: f.stat().st_mtime)
    return newest.parent


def _read_current_state(project_dir: Path) -> str:
    try:
        data = json.loads((project_dir / "run_state.json").read_text(encoding="utf-8"))
        return data.get("current_state", "unknown")
    except Exception:
        return "unknown"


def _write_heartbeat(project_dir: Path, current_state: str) -> None:
    heartbeat_path = project_dir / "heartbeat.json"
    tmp = project_dir / "heartbeat.json.tmp"
    payload = {
        "agent": "claude-code-session",
        "state": current_state,
        "message": "claude stopped",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stopped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, heartbeat_path)
    except Exception as exc:
        _log("Stop", f"heartbeat write failed: {exc}")


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    # Avoid recursion: if stop_hook_active is true, exit immediately
    if payload.get("stop_hook_active"):
        _log("Stop", "stop_hook_active=true, skipping")
        sys.exit(0)

    try:
        project_dir = _detect_project_dir()
        if project_dir is None:
            _log("Stop", "no active project_dir found")
            sys.exit(0)

        current_state = _read_current_state(project_dir)
        _write_heartbeat(project_dir, current_state)
        _log("Stop", f"wrote heartbeat to {project_dir} state={current_state}")

    except Exception as exc:
        _log("Stop", f"error: {exc}")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
