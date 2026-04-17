#!/usr/bin/env python3
"""Claude Code SessionStart hook for TrendR.

Scans ~/research for pending runs and returns additionalContext so the
host Claude Code agent is immediately aware of in-progress work.

Protocol: reads JSON from stdin (Claude Code hook payload), writes JSON
to stdout. Exits 0 on success or on any error (never block session start).
"""

import json
import os
import sys
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


def main() -> None:
    try:
        _payload = sys.stdin.read()
    except Exception:
        _payload = ""

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from engine.recovery.claude_code_resume import check_pending_runs, format_context

        runs = check_pending_runs()
        context = format_context(runs)
        _log("SessionStart", f"found {len(runs)} pending run(s)")

        if context:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
        else:
            output = {}

        print(json.dumps(output))

    except Exception as exc:
        _log("SessionStart", f"error: {exc}")
        print(json.dumps({}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
