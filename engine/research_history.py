"""User-level research history for TrendR runs.

This module keeps a local Markdown summary plus a JSON sidecar under the
repository-local `.trendr/` directory, which is already gitignored.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional


DEFAULT_HISTORY_LIMIT = 60
JSON_NAME = "research_history.json"
MARKDOWN_NAME = "research_history.md"
VALID_OVERFLOW_POLICIES = {"prompt", "fifo", "append", "skip"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _format_duration(seconds: int) -> str:
    total = max(0, int(seconds or 0))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return sum(1 for row in reader if any(str(v or "").strip() for v in row.values()))
    except Exception:
        return 0


def _count_notes(notes_dir: Path) -> int:
    if not notes_dir.exists():
        return 0
    try:
        return sum(1 for path in notes_dir.glob("*.md") if path.is_file())
    except Exception:
        return 0


def history_root(repo_root: Path) -> Path:
    override = os.environ.get("TRENDR_HISTORY_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(repo_root).expanduser().resolve() / ".trendr"


def history_paths(repo_root: Path) -> tuple[Path, Path]:
    root = history_root(repo_root)
    return root / JSON_NAME, root / MARKDOWN_NAME


def _derive_duration_sec(state: dict) -> int:
    explicit = state.get("duration_sec")
    if explicit is not None:
        try:
            return max(0, int(explicit))
        except (TypeError, ValueError):
            pass

    started = _parse_iso(state.get("started_at"))
    finished = _parse_iso(state.get("finished_at")) or _now()
    if started is None:
        return 0
    return max(0, int((finished - started).total_seconds()))


def build_record(project_dir: Path, state: dict) -> dict:
    project_dir = Path(project_dir).expanduser().resolve()
    params = state.get("params", {}) if isinstance(state.get("params"), dict) else {}
    started = _parse_iso(state.get("started_at"))
    finished = _parse_iso(state.get("finished_at"))
    duration_sec = _derive_duration_sec(state)

    return {
        "run_id": str(state.get("run_id") or ""),
        "project": str(state.get("project") or project_dir.name),
        "project_dir": str(project_dir),
        "topic": str(params.get("topic") or ""),
        "status": str(state.get("status") or "unknown"),
        "platform": str(state.get("platform") or ""),
        "profile": str(params.get("profile") or "basic"),
        "started_at": started.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if started else "",
        "finished_at": finished.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if finished else "",
        "duration_sec": duration_sec,
        "paper_count": _count_csv_rows(project_dir / "candidates.csv"),
        "notes_count": _count_notes(project_dir / "notes"),
        "discovery_rounds": int(state.get("discovery_rounds", 0) or 0),
        "fix_rounds": int(state.get("fix_rounds", 0) or 0),
        "updated_at": _now_iso(),
    }


def _load_payload(json_path: Path) -> dict:
    if not json_path.exists():
        return {
            "version": 1,
            "recommended_limit": DEFAULT_HISTORY_LIMIT,
            "generated_at": _now_iso(),
            "records": [],
        }
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    records = payload.get("records")
    payload.setdefault("version", 1)
    payload.setdefault("recommended_limit", DEFAULT_HISTORY_LIMIT)
    payload.setdefault("generated_at", _now_iso())
    payload["records"] = records if isinstance(records, list) else []
    return payload


def _local_day(value: str | None) -> Optional[date]:
    dt = _parse_iso(value)
    if dt is None:
        return None
    return dt.astimezone().date()


def _render_markdown(payload: dict) -> str:
    records = payload.get("records", [])
    recommended_limit = int(payload.get("recommended_limit") or DEFAULT_HISTORY_LIMIT)
    generated_at = payload.get("generated_at") or _now_iso()
    today = datetime.now().astimezone().date()

    completed = sum(1 for row in records if row.get("status") == "completed")
    failed = sum(1 for row in records if row.get("status") == "failed")
    total_duration = sum(int(row.get("duration_sec", 0) or 0) for row in records)
    total_papers = sum(int(row.get("paper_count", 0) or 0) for row in records)
    today_records = [row for row in records if _local_day(row.get("started_at")) == today]
    today_duration = sum(int(row.get("duration_sec", 0) or 0) for row in today_records)
    today_papers = sum(int(row.get("paper_count", 0) or 0) for row in today_records)

    lines = [
        "# TrendR Research History",
        "",
        f"- Updated: {generated_at}",
        f"- Recommended Limit: {recommended_limit}",
        f"- Current Records: {len(records)}",
        "",
        "## Summary",
        f"- Total Runs: {len(records)}",
        f"- Completed Runs: {completed}",
        f"- Failed Runs: {failed}",
        f"- Overall Search Time: {_format_duration(total_duration)}",
        f"- Overall Paper Count: {total_papers}",
        f"- Today's Runs: {len(today_records)}",
        f"- Today's Search Time: {_format_duration(today_duration)}",
        f"- Today's Paper Count: {today_papers}",
        "",
        "## Recent Runs",
        "",
        "| # | Started | Topic | Status | Time | Papers | Notes | Platform | Project |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for index, row in enumerate(reversed(records), start=1):
        started = str(row.get("started_at") or "-")[:19].replace("T", " ")
        topic = str(row.get("topic") or "-").replace("|", "/")
        status = str(row.get("status") or "-").replace("|", "/")
        duration = _format_duration(int(row.get("duration_sec", 0) or 0))
        papers = int(row.get("paper_count", 0) or 0)
        notes = int(row.get("notes_count", 0) or 0)
        platform = str(row.get("platform") or "-").replace("|", "/")
        project = str(row.get("project") or "-").replace("|", "/")
        lines.append(
            f"| {index} | {started} | {topic} | {status} | {duration} | {papers} | {notes} | {platform} | {project} |"
        )

    lines.append("")
    return "\n".join(lines)


def _resolve_overflow_action(
    count: int,
    limit: int,
    policy: str,
    prompt_fn: Callable[[str], str],
    interactive: bool,
) -> str:
    if count < limit:
        return "add"

    normalized = str(policy or "prompt").strip().lower()
    if normalized not in VALID_OVERFLOW_POLICIES:
        normalized = "prompt"

    if normalized == "fifo":
        return "fifo"
    if normalized == "append":
        return "append"
    if normalized == "skip":
        return "skip"
    if not interactive:
        return "fifo"

    reply = prompt_fn(
        f"TrendR history already has {limit} records. "
        "[f] FIFO drop oldest and add new, [a] append anyway, [s] skip new entry? [f/a/s]: "
    ).strip().lower()
    if reply == "a":
        return "append"
    if reply == "s":
        return "skip"
    return "fifo"


def update_research_history(
    repo_root: Path,
    project_dir: Path,
    state: dict,
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
    overflow_policy: str = "prompt",
    prompt_fn: Callable[[str], str] = input,
    interactive: bool | None = None,
) -> dict:
    """Upsert a run into the local research history and regenerate Markdown."""
    repo_root = Path(repo_root).expanduser().resolve()
    project_dir = Path(project_dir).expanduser().resolve()
    json_path, markdown_path = history_paths(repo_root)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    payload = _load_payload(json_path)
    records = payload.get("records", [])
    limit = max(1, int(limit or DEFAULT_HISTORY_LIMIT))
    interactive = bool(interactive) if interactive is not None else False
    record = build_record(project_dir, state)

    match_index = next(
        (
            index
            for index, row in enumerate(records)
            if row.get("run_id") == record["run_id"] and row.get("project_dir") == record["project_dir"]
        ),
        None,
    )

    action = "updated"
    overflow_action = "none"
    if match_index is not None:
        records[match_index] = record
    else:
        overflow_action = _resolve_overflow_action(
            count=len(records),
            limit=limit,
            policy=overflow_policy,
            prompt_fn=prompt_fn,
            interactive=interactive,
        )
        if overflow_action == "skip":
            action = "skipped"
        else:
            if overflow_action == "fifo" and len(records) >= limit:
                records = records[-(limit - 1):] if limit > 1 else []
            records.append(record)
            action = "added"

    payload["recommended_limit"] = limit
    payload["generated_at"] = _now_iso()
    payload["overflow_policy"] = overflow_policy
    payload["records"] = records
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")

    return {
        "action": action,
        "overflow_action": overflow_action,
        "record_count": len(records),
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "recommended_limit": limit,
    }
