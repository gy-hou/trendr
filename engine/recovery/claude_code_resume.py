"""Shared utility for Claude Code SessionStart hook and cli.py status command.

Scans ~/research for pending TrendR runs and formats context strings.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def check_pending_runs(
    root: Path = Path.home() / "research",
    limit: int = 5,
) -> list[dict]:
    """Return pending runs (status in {running, paused, failed}), newest first.

    Args:
        root: Directory to scan for run_state.json files.
        limit: Maximum number of runs to return.

    Returns:
        List of dicts with keys: project_dir, status, current_state, updated_at, run_id.
    """
    pending = []

    if not root.exists():
        return pending

    for state_file in root.glob("*/run_state.json"):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        status = data.get("status", "")
        if status not in {"running", "paused", "failed"}:
            continue

        updated_at = data.get("updated_at") or data.get("started_at") or ""
        pending.append(
            {
                "project_dir": str(state_file.parent),
                "status": status,
                "current_state": data.get("current_state", "?"),
                "updated_at": updated_at,
                "run_id": data.get("run_id", "?"),
                "topic": data.get("topic", ""),
            }
        )

    pending.sort(key=lambda r: r["updated_at"], reverse=True)
    return pending[:limit]


def _age_str(updated_at: str) -> str:
    """Return human-readable age like '12m ago' or 'just now'."""
    if not updated_at:
        return "unknown time ago"
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        seconds = int((now - dt).total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except (ValueError, TypeError):
        return "unknown time ago"


def format_context(runs: Iterable[dict]) -> str:
    """One-line-per-run context string for SessionStart additionalContext.

    Args:
        runs: Iterable of run dicts from check_pending_runs().

    Returns:
        Multi-line string suitable for Claude Code additionalContext.
    """
    runs_list = list(runs)
    if not runs_list:
        return ""

    lines = [f"TrendR: {len(runs_list)} run(s) pending."]
    for r in runs_list:
        project_name = Path(r["project_dir"]).name
        age = _age_str(r["updated_at"])
        topic_hint = f" [{r['topic']}]" if r.get("topic") else ""
        lines.append(
            f"  • {project_name}{topic_hint} — state={r['current_state']} "
            f"status={r['status']} updated={age}"
        )
    lines.append("Run `/tr resume <project-dir>` to continue a paused run.")
    return "\n".join(lines)
