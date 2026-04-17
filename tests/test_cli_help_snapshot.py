"""Snapshot tests for CLI help output.

Detects unintentional regressions in help text caused by argparse changes.
To update snapshots: delete the snapshot files and re-run the tests once.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "cli.py"
SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"


def _get_help(args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI)] + args,
        capture_output=True,
        cwd=str(REPO),
        timeout=10,
    )
    return (result.stdout + result.stderr).decode(errors="replace").strip()


@pytest.mark.parametrize(
    "args,snapshot_name",
    [
        (["--help"], "cli_help.txt"),
        (["run", "--help"], "cli_run_help.txt"),
        (["hotspots", "--help"], "cli_hotspots_help.txt"),
    ],
)
def test_cli_help_matches_snapshot(args, snapshot_name):
    snapshot_path = SNAPSHOTS_DIR / snapshot_name
    current_output = _get_help(args)

    if not snapshot_path.exists():
        snapshot_path.write_text(current_output, encoding="utf-8")
        pytest.skip(f"Snapshot {snapshot_name} created — re-run to verify")

    expected = snapshot_path.read_text(encoding="utf-8").strip()
    assert current_output == expected, (
        f"CLI help output changed for `{' '.join(args)}`.\n"
        f"Delete tests/snapshots/{snapshot_name} and re-run to update."
    )
