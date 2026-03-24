#!/usr/bin/env python3
"""TrendR overnight supervisor: monitor progress, resume stuck runs, and stop when done."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

TERMINAL_STATUS = {"completed", "failed", "cancelled", "canceled"}

PHASE_RANK = {
    "init": 0,
    "phase0": 0,
    "phase_0": 0,
    "phase1": 1,
    "phase_1": 1,
    "discovery": 1,
    "phase2": 2,
    "phase_2": 2,
    "analysis": 2,
    "phase3": 3,
    "phase_3": 3,
    "gap_check": 3,
    "phase4": 4,
    "phase_4": 4,
    "writing": 4,
    "phase5": 5,
    "phase_5": 5,
    "persist": 5,
    "report": 5,
}

CHECKPOINT_RANK = {
    "none": 0,
    "phase1_ready": 1,
    "phase2_ready": 2,
    "phase4_ready": 4,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def normalize_phase(value: Any) -> str:
    phase = str(value or "init").strip().lower().replace(" ", "_").replace("-", "_")
    return phase or "init"


def phase_rank(value: Any) -> int:
    phase = normalize_phase(value)
    if phase in PHASE_RANK:
        return PHASE_RANK[phase]
    if phase.startswith("phase") and phase[-1:].isdigit():
        return int(phase[-1:])
    return 0


def csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        lines = [line for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
        if len(lines) <= 1:
            return 0
        return len(lines) - 1
    except Exception:
        return 0


def notes_count(notes_dir: Path) -> int:
    if not notes_dir.exists() or not notes_dir.is_dir():
        return 0
    return len(list(notes_dir.glob("*.md")))


def detect_checkpoint(base_dir: Path) -> Tuple[str, Dict[str, int]]:
    candidates = base_dir / "candidates.csv"
    search_log = base_dir / "search_log.md"
    matrix = base_dir / "matrix.csv"
    notes_dir = base_dir / "notes"
    review = base_dir / "review.md"
    references = base_dir / "references.bib"

    candidate_rows = csv_rows(candidates)
    note_files = notes_count(notes_dir)

    phase1_ready = candidate_rows > 0 and search_log.exists()
    phase2_ready = phase1_ready and matrix.exists() and note_files > 0
    phase4_ready = phase2_ready and review.exists() and references.exists()

    details = {
        "candidate_rows": candidate_rows,
        "note_files": note_files,
        "has_search_log": int(search_log.exists()),
        "has_matrix": int(matrix.exists()),
        "has_review": int(review.exists()),
        "has_references": int(references.exists()),
    }

    if phase4_ready:
        return "phase4_ready", details
    if phase2_ready:
        return "phase2_ready", details
    if phase1_ready:
        return "phase1_ready", details
    return "none", details


def latest_activity_epoch(base_dir: Path, run_status: Path, progress: Path) -> float:
    candidates = base_dir / "candidates.csv"
    search_log = base_dir / "search_log.md"
    matrix = base_dir / "matrix.csv"
    review = base_dir / "review.md"
    references = base_dir / "references.bib"
    notes_dir = base_dir / "notes"

    # Ignore supervisor-owned logs. Otherwise the guard keeps resetting its own
    # idle timer and can never detect a genuinely stalled run.
    tracked = [run_status, progress, candidates, search_log, matrix, review, references]
    if notes_dir.exists() and notes_dir.is_dir():
        tracked.extend(sorted(notes_dir.glob("*.md")))
    mtimes = []
    for path in tracked:
        try:
            if path.exists():
                mtimes.append(path.stat().st_mtime)
        except Exception:
            continue
    if not mtimes:
        return time.time()
    return max(mtimes)


def append_log(run_log: Path, latest_log: Path, line: str) -> None:
    run_log.parent.mkdir(parents=True, exist_ok=True)
    content = f"[{now_iso()}] [supervisor] {line}\n"
    with run_log.open("a", encoding="utf-8") as fp:
        fp.write(content)
    try:
        shutil.copy2(run_log, latest_log)
    except Exception:
        pass


def build_overnight_report(
    project: str,
    run_id: str,
    base_dir: Path,
    status_text: str,
    phase: str,
    checkpoint: str,
    idle_sec: int,
    state: Dict[str, Any],
    decision_reason: str,
    decision_action: str,
    next_step: str,
) -> str:
    lines = [
        "# TrendR Overnight Report",
        f"- project: {project}",
        f"- run_id: {run_id}",
        f"- generated_at_utc: {now_iso()}",
        "",
        "## Runtime Snapshot",
        f"- run_status.status: {status_text}",
        f"- run_status.phase: {phase}",
        f"- detected_checkpoint: {checkpoint}",
        f"- idle_seconds: {idle_sec}",
        f"- resume_count: {int(state.get('resume_count') or 0)}",
        f"- last_resume_reason: {state.get('last_resume_reason') or 'N/A'}",
        f"- last_resume_ok: {state.get('last_resume_ok') if 'last_resume_ok' in state else 'N/A'}",
        "",
        "## Supervisor Decision",
        f"- reason: {decision_reason}",
        f"- action: {decision_action}",
        "",
        "## Next Step",
        f"- {next_step}",
        "",
        "## Key Files",
        f"- {base_dir / 'run_status.json'}",
        f"- {base_dir / 'progress.md'}",
        f"- {base_dir / 'logs' / f'{run_id}.log'}",
        f"- {base_dir / 'logs' / f'supervisor_{run_id}.json'}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_overnight_report(report_path: Path, latest_report_path: Path, content: str) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
    try:
        shutil.copy2(report_path, latest_report_path)
    except Exception:
        pass


def resolve_session_id(args: argparse.Namespace, run_status_payload: Dict[str, Any], state: Dict[str, Any]) -> Optional[str]:
    if args.session_id:
        return args.session_id
    owner = str(run_status_payload.get("owner_session_id") or "").strip()
    if owner:
        return owner
    cached = str(state.get("session_id") or "").strip()
    if cached:
        return cached
    return None


def build_resume_message(project: str, run_id: str, phase: str, checkpoint: str, idle_sec: int) -> str:
    prefix = (
        f"[TrendR supervisor auto-resume] project={project}, run_id={run_id}, "
        f"phase={phase}, idle={idle_sec}s.\n"
    )

    if checkpoint == "phase4_ready":
        return prefix + (
            "Detected research outputs already exist (review.md + references.bib). "
            "Finalize the run now: refresh run_status.json/progress.md, write the completion summary, "
            "and mark status=completed with finished_at/duration_sec. Skip duplicate work if outputs are valid."
        )

    if checkpoint == "phase2_ready":
        return prefix + (
            "Detected Phase 2 outputs already exist (matrix.csv + notes). "
            "Continue from Phase 3 Gap Check immediately, then proceed to Phase 4 Writing. "
            "Do not re-run finished steps unless files are corrupted."
        )

    if checkpoint == "phase1_ready":
        return prefix + (
            "Detected Phase 1 outputs already exist (candidates.csv + search_log.md). "
            "Continue with Phase 2 Analysis now: read candidates.csv, select relevance>=4, "
            "dispatch paper-analyzer, and keep 5-10 min heartbeat updates."
        )

    return prefix + (
        "No valid Phase 1 artifacts detected yet. "
        "Re-dispatch paper-scout with fallback search enabled and force-write "
        "candidates.csv + search_log.md before moving on."
    )


def send_resume(session_id: str, message: str, message_timeout_sec: int, dry_run: bool) -> Tuple[bool, str]:
    if dry_run:
        return True, "dry-run: message not sent"

    cmd = [
        "openclaw",
        "agent",
        "--session-id",
        session_id,
        "--message",
        message,
        "--timeout",
        str(message_timeout_sec),
        "--json",
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        return True, out.strip()[:1200]
    return False, out.strip()[:1200]


def should_resume(
    current_phase_rank: int,
    checkpoint_rank: int,
    idle_sec: int,
    idle_timeout_sec: int,
    phase_mismatch_grace_sec: int,
) -> Tuple[bool, str]:
    if checkpoint_rank > current_phase_rank and idle_sec >= phase_mismatch_grace_sec:
        return True, "phase_mismatch"
    if idle_sec >= idle_timeout_sec:
        return True, "idle_timeout"
    return False, ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TrendR overnight supervisor")
    parser.add_argument("--project", required=True, help="Project name under ~/research")
    parser.add_argument("--base-dir", default="~/research", help="Base directory for projects")
    parser.add_argument("--run-id", default="", help="RUN_ID; defaults to logs/.current_run_id")
    parser.add_argument("--session-id", default="", help="Owner session id for auto-injection")
    parser.add_argument("--poll-sec", type=int, default=60, help="Polling interval seconds")
    parser.add_argument("--idle-timeout-sec", type=int, default=600, help="Idle timeout before resume")
    parser.add_argument(
        "--phase-mismatch-grace-sec",
        type=int,
        default=180,
        help="Grace period for detected checkpoint/phase mismatch",
    )
    parser.add_argument(
        "--artifact-complete-grace-sec",
        type=int,
        default=1800,
        help="Exit if review artifacts stay stable for this many seconds",
    )
    parser.add_argument(
        "--resume-cooldown-sec",
        type=int,
        default=300,
        help="Minimum interval between two resume injections",
    )
    parser.add_argument("--max-resume", type=int, default=12, help="Maximum resume injections per run")
    parser.add_argument("--heartbeat-sec", type=int, default=300, help="Heartbeat log interval")
    parser.add_argument("--message-timeout-sec", type=int, default=120, help="openclaw agent timeout")
    parser.add_argument("--dry-run", action="store_true", help="Do not send openclaw message")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_root = Path(os.path.expanduser(args.base_dir))
    base_dir = base_root / args.project
    logs_dir = base_dir / "logs"
    run_status_path = base_dir / "run_status.json"
    progress_path = base_dir / "progress.md"
    latest_log_path = logs_dir / "latest.log"
    current_run_path = logs_dir / ".current_run_id"

    logs_dir.mkdir(parents=True, exist_ok=True)

    run_id = args.run_id.strip()
    if not run_id and current_run_path.exists():
        run_id = current_run_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_log_path = logs_dir / f"{run_id}.log"
    state_path = logs_dir / f"supervisor_{run_id}.json"
    report_path = logs_dir / f"overnight_report_{run_id}.md"
    latest_report_path = logs_dir / "overnight_report.md"

    state = safe_read_json(state_path)
    state.setdefault("run_id", run_id)
    state.setdefault("resume_count", 0)
    state.setdefault("last_resume_epoch", 0)
    state.setdefault("last_heartbeat_epoch", 0)
    state.setdefault("max_resume_notified", False)

    append_log(
        run_log_path,
        latest_log_path,
        (
            f"supervisor started: run_id={run_id}, project={args.project}, poll={args.poll_sec}s, "
            f"idle_timeout={args.idle_timeout_sec}s, artifact_complete_grace={args.artifact_complete_grace_sec}s, "
            f"dry_run={args.dry_run}"
        ),
    )

    while True:
        status_payload = safe_read_json(run_status_path)
        status_text = str(status_payload.get("status") or "running").strip().lower()
        phase = normalize_phase(status_payload.get("phase") or "init")
        current_phase_rank = phase_rank(phase)

        session_id = resolve_session_id(args, status_payload, state)
        if session_id and state.get("session_id") != session_id:
            state["session_id"] = session_id

        checkpoint, details = detect_checkpoint(base_dir)
        checkpoint_rank = CHECKPOINT_RANK.get(checkpoint, 0)

        now_epoch = time.time()
        last_activity = latest_activity_epoch(base_dir, run_status_path, progress_path)
        idle_sec = int(max(0, now_epoch - last_activity))

        if status_text in TERMINAL_STATUS:
            state["stopped_reason"] = f"terminal_status:{status_text}"
            append_log(run_log_path, latest_log_path, f"terminal status detected ({status_text}); supervisor exits")
            write_overnight_report(
                report_path=report_path,
                latest_report_path=latest_report_path,
                content=build_overnight_report(
                    project=args.project,
                    run_id=run_id,
                    base_dir=base_dir,
                    status_text=status_text,
                    phase=phase,
                    checkpoint=checkpoint,
                    idle_sec=idle_sec,
                    state=state,
                    decision_reason=state["stopped_reason"],
                    decision_action="exit",
                    next_step=(
                        "If completed, archive outputs. If failed/cancelled, inspect latest.log and rerun the failed phase."
                    ),
                ),
            )
            safe_write_json(state_path, state)
            return 0

        if checkpoint == "phase4_ready" and idle_sec >= max(args.artifact_complete_grace_sec, 1):
            state["stopped_reason"] = "artifact_complete"
            append_log(
                run_log_path,
                latest_log_path,
                (
                    "review artifacts stable long enough; supervisor exits without further resume "
                    f"(idle={idle_sec}s)"
                ),
            )
            write_overnight_report(
                report_path=report_path,
                latest_report_path=latest_report_path,
                content=build_overnight_report(
                    project=args.project,
                    run_id=run_id,
                    base_dir=base_dir,
                    status_text=status_text,
                    phase=phase,
                    checkpoint=checkpoint,
                    idle_sec=idle_sec,
                    state=state,
                    decision_reason=state["stopped_reason"],
                    decision_action="exit",
                    next_step=(
                        "Validate review.md/references.bib quickly, then set run_status.json status=completed if not yet finalized."
                    ),
                ),
            )
            safe_write_json(state_path, state)
            return 0

        heartbeat_due = now_epoch - float(state.get("last_heartbeat_epoch") or 0) >= max(args.heartbeat_sec, 1)
        if heartbeat_due:
            append_log(
                run_log_path,
                latest_log_path,
                (
                    f"heartbeat phase={phase} checkpoint={checkpoint} idle={idle_sec}s "
                    f"resume_count={state.get('resume_count', 0)}"
                ),
            )
            state["last_heartbeat_epoch"] = int(now_epoch)

        resume_due, reason = should_resume(
            current_phase_rank=current_phase_rank,
            checkpoint_rank=checkpoint_rank,
            idle_sec=idle_sec,
            idle_timeout_sec=args.idle_timeout_sec,
            phase_mismatch_grace_sec=args.phase_mismatch_grace_sec,
        )

        cooldown_ok = now_epoch - float(state.get("last_resume_epoch") or 0) >= max(args.resume_cooldown_sec, 1)
        under_limit = int(state.get("resume_count") or 0) < max(args.max_resume, 1)

        if resume_due and not under_limit and not state.get("max_resume_notified"):
            append_log(
                run_log_path,
                latest_log_path,
                f"resume suppressed: max_resume reached ({state.get('resume_count', 0)})",
            )
            write_overnight_report(
                report_path=report_path,
                latest_report_path=latest_report_path,
                content=build_overnight_report(
                    project=args.project,
                    run_id=run_id,
                    base_dir=base_dir,
                    status_text=status_text,
                    phase=phase,
                    checkpoint=checkpoint,
                    idle_sec=idle_sec,
                    state=state,
                    decision_reason="max_resume_reached",
                    decision_action="continue_monitoring_without_injection",
                    next_step=(
                        "Manual intervention recommended: inspect latest.log/run_status.json, then restart the stalled phase."
                    ),
                ),
            )
            state["max_resume_notified"] = True

        if resume_due and cooldown_ok and under_limit:
            if not session_id:
                append_log(
                    run_log_path,
                    latest_log_path,
                    "resume needed but missing session_id; set owner_session_id in run_status.json",
                )
            else:
                message = build_resume_message(
                    project=args.project,
                    run_id=run_id,
                    phase=phase,
                    checkpoint=checkpoint,
                    idle_sec=idle_sec,
                )
                ok, info = send_resume(
                    session_id=session_id,
                    message=message,
                    message_timeout_sec=args.message_timeout_sec,
                    dry_run=args.dry_run,
                )
                state["last_resume_epoch"] = int(now_epoch)
                state["resume_count"] = int(state.get("resume_count") or 0) + 1
                state["last_resume_reason"] = reason
                state["last_resume_ok"] = bool(ok)
                state["max_resume_notified"] = False
                if ok:
                    append_log(
                        run_log_path,
                        latest_log_path,
                        f"resume injected (reason={reason}, checkpoint={checkpoint}, session={session_id})",
                    )
                else:
                    append_log(
                        run_log_path,
                        latest_log_path,
                        (
                            "resume injection failed "
                            f"(reason={reason}, checkpoint={checkpoint}, session={session_id}): {info}"
                        ),
                    )

        safe_write_json(state_path, state)

        if args.once:
            return 0

        time.sleep(max(args.poll_sec, 5))


if __name__ == "__main__":
    raise SystemExit(main())
