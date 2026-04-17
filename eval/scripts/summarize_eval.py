#!/usr/bin/env python3
"""Summarize evaluation runs into markdown tables."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / "eval"
TREND_R_RUNS = EVAL_ROOT / "runs" / "trendr"
BASELINE_RUNS = EVAL_ROOT / "runs" / "baseline"
SUMMARY_PATH = EVAL_ROOT / "results" / "summary_table.md"
FAILURE_PATH = EVAL_ROOT / "results" / "failure_cases.md"


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def collect_trendr_stats() -> dict[str, float | int | str]:
    run_states = list(TREND_R_RUNS.glob("**/run_state.json"))
    if not run_states:
        return {
            "trendr_runs": 0,
            "stable_completion_rate": "pending",
            "resume_success_rate": "pending",
            "analysis_fallback_trigger_rate": "pending",
        }

    total = len(run_states)
    completed = 0
    fallback = 0
    resumes = 0
    resume_success = 0

    for path in run_states:
        state = load_json(path) or {}
        history = state.get("history", []) or []
        if state.get("status") == "completed":
            completed += 1
        if any("fallback" in str(entry).lower() for entry in history):
            fallback += 1
        resume_path = path.parent / "resume_request.json"
        if resume_path.exists():
            resumes += 1
            if state.get("status") == "completed":
                resume_success += 1

    stable_completion_rate = completed / total if total else 0.0
    fallback_rate = fallback / total if total else 0.0
    resume_rate = (resume_success / resumes) if resumes else "n/a"
    return {
        "trendr_runs": total,
        "stable_completion_rate": stable_completion_rate,
        "resume_success_rate": resume_rate,
        "analysis_fallback_trigger_rate": fallback_rate,
    }


def collect_baseline_stats() -> dict[str, float | int | str]:
    runs = list(BASELINE_RUNS.glob("**/baseline_run_meta.json"))
    if not runs:
        return {"baseline_runs": 0, "stable_completion_rate": "pending"}
    return {"baseline_runs": len(runs), "stable_completion_rate": "pending"}


def render_summary(trendr: dict, baseline: dict) -> str:
    return "\n".join(
        [
            "# Summary Table",
            "",
            "| metric | trendr | baseline | notes |",
            "|---|---:|---:|---|",
            f"| resume_success_rate | {trendr['resume_success_rate']} | n/a | from resume_request + final status |",
            "| citation_detection_recall | pending | n/a | requires injected-error runs |",
            "| citation_detection_precision | pending | n/a | requires injected-error runs |",
            "| high_relevance_coverage | pending | pending | requires gold-set mapping |",
            f"| analysis_fallback_trigger_rate | {trendr['analysis_fallback_trigger_rate']} | n/a | from run history signals |",
            f"| stable_completion_rate | {trendr['stable_completion_rate']} | {baseline['stable_completion_rate']} | completion stability comparison |",
        ]
    ) + "\n"


def main() -> None:
    trendr = collect_trendr_stats()
    baseline = collect_baseline_stats()

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(trendr, baseline), encoding="utf-8")

    if not FAILURE_PATH.exists():
        FAILURE_PATH.write_text("# Failure Cases\n\n", encoding="utf-8")


if __name__ == "__main__":
    main()
