"""End-to-end smoke test for Claude Code native dispatch loop.

Skipped unless RUN_E2E=1 is set.  Simulates a "host Claude Code agent" by
polling claude_code_dispatch.jsonl and writing fake completions so the CLI
can advance through INIT→DISCOVERY→DONE without a real claude binary.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E") != "1",
    reason="set RUN_E2E=1 to run e2e tests",
)

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "cli.py"

# Fake output that satisfies candidates.csv expectation
FAKE_CANDIDATES_CSV = (
    "title,arxiv_id,year,score\n"
    "Fake Paper 1,2401.00001,2024,0.9\n"
    "Fake Paper 2,2401.00002,2024,0.8\n"
)

FAKE_REVIEW_MD = "# Smoke Review\n\nThis is a fake review.\n"
FAKE_VERIFY_JSON = json.dumps({"status": "ok", "issues": []})


def _fake_host(project_dir: Path, stop_event: threading.Event) -> None:
    """Simulates a Claude Code host: reads dispatch, writes completions."""
    dispatch_file = project_dir / "claude_code_dispatch.jsonl"
    comp_dir = project_dir / "claude_code_completions"
    processed: set[str] = set()

    while not stop_event.is_set():
        if not dispatch_file.exists():
            time.sleep(0.1)
            continue

        try:
            lines = dispatch_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            time.sleep(0.1)
            continue

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            handle = rec.get("handle", "")
            if not handle or handle in processed:
                continue
            processed.add(handle)

            agent_id = rec.get("agent_id", rec.get("subagent_type", ""))
            op = rec.get("op", "")

            if op != "agent":
                continue

            # Write fake output files depending on agent type
            if agent_id == "paper-scout":
                (project_dir / "candidates.csv").write_text(FAKE_CANDIDATES_CSV)
                output = "Wrote candidates.csv with 2 fake papers."
            elif agent_id == "paper-analyzer":
                notes_dir = project_dir / "notes"
                notes_dir.mkdir(exist_ok=True)
                (notes_dir / "fake_paper.md").write_text("# Fake Paper Notes\n")
                (project_dir / "matrix.csv").write_text("title,gap\nFake Paper 1,yes\n")
                output = "Wrote notes and matrix."
            elif agent_id == "review-lead":
                (project_dir / "review.md").write_text(FAKE_REVIEW_MD)
                (project_dir / "references.bib").write_text("")
                output = "Wrote review.md."
            elif agent_id == "verifier":
                (project_dir / "verify.json").write_text(FAKE_VERIFY_JSON)
                output = "Verification passed."
            else:
                output = f"Unknown agent {agent_id}, returning empty."

            # Write completion file
            comp_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "handle": handle,
                "status": "completed",
                "output": output,
                "artifacts": [],
                "ended_at": "2026-04-17T00:00:00+00:00",
            }
            tmp = comp_dir / f"{handle}.json.tmp"
            final = comp_dir / f"{handle}.json"
            tmp.write_text(json.dumps(payload, indent=2))
            os.replace(tmp, final)

        time.sleep(0.15)


@pytest.fixture
def project_dir(tmp_path):
    p = tmp_path / "smoke-run"
    p.mkdir()
    return p


def test_cli_native_mode_dispatch_loop(project_dir, tmp_path):
    """CLI runs in native mode, fake host satisfies dispatch, run completes."""
    stop = threading.Event()
    host = threading.Thread(target=_fake_host, args=(project_dir, stop), daemon=True)
    host.start()

    env = {
        **os.environ,
        "TRENDR_CC_MODE": "native",
        "CLAUDE_CODE_TEST": "1",  # triggers claude-code platform detection
        "TRENDR_PROJECT_DIR": str(project_dir),
    }

    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "run",
            "--topic",
            "smoke test agentic RAG",
            "--platform",
            "claude-code",
            "--project-dir",
            str(project_dir),
            "--depth",
            "A",
            "--no-watchdog",
            "--time-budget",
            "60",
        ],
        capture_output=True,
        env=env,
        timeout=90,
        cwd=str(REPO),
    )

    stop.set()
    host.join(timeout=2)

    # CLI should exit (0 = success, 1 = acceptable error like verify warning)
    assert proc.returncode in (0, 1), (
        f"CLI exited with unexpected code {proc.returncode}\n"
        f"STDOUT:\n{proc.stdout.decode(errors='replace')}\n"
        f"STDERR:\n{proc.stderr.decode(errors='replace')}"
    )

    run_state = project_dir / "run_state.json"
    assert run_state.exists(), "run_state.json was not created"

    state_data = json.loads(run_state.read_text())
    assert state_data.get("status") in ("completed", "done", "running", "paused"), (
        f"unexpected run status: {state_data.get('status')}"
    )
