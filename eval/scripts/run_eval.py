#!/usr/bin/env python3
"""Run evaluation batches for TrendR and baseline modes.

This script scaffolds repeatable runs and persists metadata under eval/runs/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / "eval"
TOPICS_DIR = EVAL_ROOT / "topics"
RUNS_DIR = EVAL_ROOT / "runs"


def load_topics() -> list[dict[str, str]]:
    topics: list[dict[str, str]] = []
    for path in sorted(TOPICS_DIR.glob("*.yaml")):
        record: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            record[k.strip()] = v.strip().strip('"')
        if "id" in record and "query" in record:
            topics.append(record)
    return topics


def run_trendr(topic: dict[str, str], repeat: int, execute: bool, platform: str) -> None:
    for i in range(repeat):
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = RUNS_DIR / "trendr" / topic["id"] / f"run_{i+1}_{run_id}"
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "python3",
            "cli.py",
            "run",
            "--topic",
            topic["query"],
            "--platform",
            platform,
            "--project-dir",
            str(out_dir),
        ]
        meta = {
            "mode": "trendr",
            "topic": topic,
            "command": cmd,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "executed": execute,
        }
        if execute:
            t0 = time.time()
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            meta["return_code"] = proc.returncode
            meta["duration_sec"] = round(time.time() - t0, 3)
            meta["stdout_tail"] = "\n".join(proc.stdout.splitlines()[-30:])
            meta["stderr_tail"] = "\n".join(proc.stderr.splitlines()[-30:])
        (out_dir / "eval_run_meta.json").parent.mkdir(parents=True, exist_ok=True)
        (out_dir / "eval_run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def run_baseline(topic: dict[str, str], repeat: int) -> None:
    for i in range(repeat):
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = RUNS_DIR / "baseline" / topic["id"] / f"run_{i+1}_{run_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": "baseline",
            "topic": topic,
            "note": "Populate review.md and references.bib from your single-shot baseline process.",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        (out_dir / "baseline_run_meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TrendR evaluation batches")
    parser.add_argument("--mode", choices=["trendr", "baseline", "all"], default="all")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--platform", default="codex")
    parser.add_argument("--execute", action="store_true", help="Actually execute TrendR runs")
    args = parser.parse_args()

    topics = load_topics()
    if not topics:
        raise SystemExit("No topics found under eval/topics")

    for topic in topics:
        if args.mode in ("trendr", "all"):
            run_trendr(topic, args.repeat, args.execute, args.platform)
        if args.mode in ("baseline", "all"):
            run_baseline(topic, args.repeat)


if __name__ == "__main__":
    main()
