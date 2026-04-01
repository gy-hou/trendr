#!/usr/bin/env python3
"""TrendR v2 — Research-agent harness CLI entry point.

Usage:
    python cli.py run --topic "RL multi-agent market making" --platform openclaw
    python cli.py run --topic "..." --platform cli
    python cli.py resume ~/research/my-project   # resume from run_state.json

See ARCHITECTURE.md for the full specification.
"""

import argparse
import logging
import os
import sys
from pathlib import Path


DEPTH_PRESETS = {
    "A": {"min_papers": 20, "target_papers": 30, "min_rounds": 2, "max_rounds": 3},
    "B": {"min_papers": 30, "target_papers": 45, "min_rounds": 2, "max_rounds": 6},
    "C": {"min_papers": 50, "target_papers": 80, "min_rounds": 3, "max_rounds": 10},
}


def detect_platform() -> str:
    """Auto-detect which platform we're running on."""
    if os.environ.get("OPENCLAW_SESSION_ID"):
        return "openclaw"
    return "cli"


def get_adapter(platform: str):
    """Instantiate the appropriate platform adapter."""
    if platform == "openclaw":
        from engine.adapters.openclaw import OpenClawAdapter
        return OpenClawAdapter(mode="cli")
    elif platform == "cli":
        from engine.adapters.cli import CLIAdapter
        return CLIAdapter(repo_root=Path(__file__).parent)
    else:
        print(f"Error: Unknown platform '{platform}'. Available: openclaw, cli", file=sys.stderr)
        sys.exit(1)


def sanitize_project_name(topic: str) -> str:
    """Convert topic string to a safe directory name."""
    # Take first 50 chars, lowercase, replace spaces/special with hyphens
    name = topic.lower().strip()[:50]
    safe = ""
    for c in name:
        if c.isalnum():
            safe += c
        elif c in " -_":
            safe += "-"
    # Collapse multiple hyphens
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-") or "research"


def resolve_run_params(
    depth: str,
    min_papers: int | None = None,
    target_papers: int | None = None,
    min_rounds: int | None = None,
    max_rounds: int | None = None,
) -> dict:
    """Resolve run thresholds from depth presets plus optional overrides."""
    preset = DEPTH_PRESETS.get(depth.upper(), DEPTH_PRESETS["B"])
    resolved_min_papers = max(1, int(min_papers if min_papers is not None else preset["min_papers"]))
    resolved_max_rounds = max(1, int(max_rounds if max_rounds is not None else preset["max_rounds"]))
    resolved_min_rounds = max(
        1,
        min(int(min_rounds if min_rounds is not None else preset["min_rounds"]), resolved_max_rounds),
    )
    resolved_target_papers = max(
        resolved_min_papers,
        int(target_papers if target_papers is not None else preset["target_papers"]),
    )
    return {
        "min_papers": resolved_min_papers,
        "target_papers": resolved_target_papers,
        "min_rounds": resolved_min_rounds,
        "max_rounds": resolved_max_rounds,
    }


def cmd_run(args):
    """Start a new research run."""
    from engine.state_machine import ResearchStateMachine

    platform = args.platform or detect_platform()
    adapter = get_adapter(platform)

    # Determine project directory
    if args.project_dir:
        project_dir = Path(args.project_dir).expanduser().resolve()
    else:
        project_name = sanitize_project_name(args.topic)
        project_dir = Path.home() / "research" / project_name

    project_dir.mkdir(parents=True, exist_ok=True)

    run_params = resolve_run_params(
        depth=args.depth.upper(),
        min_papers=args.min_papers,
        target_papers=args.target_papers,
        min_rounds=args.min_rounds,
        max_rounds=args.max_rounds,
    )

    sm = ResearchStateMachine(project_dir, adapter)
    sm.initialize(
        topic=args.topic,
        depth=args.depth.upper(),
        min_papers=run_params["min_papers"],
        target_papers=run_params["target_papers"],
        min_rounds=run_params["min_rounds"],
        max_rounds=run_params["max_rounds"],
        time_budget_min=args.time_budget,
    )

    print(f"TrendR v2 — Starting research run")
    print(f"  Topic:   {args.topic}")
    print(f"  Depth:   {args.depth.upper()}")
    print(f"  Dir:     {project_dir}")
    print(f"  Platform: {platform}")
    print(
        "  Discovery: "
        f"min={run_params['min_papers']} "
        f"target={run_params['target_papers']} "
        f"min_rounds={run_params['min_rounds']} "
        f"max_rounds={run_params['max_rounds']}"
    )
    print()

    # Optionally start watchdog
    if not args.no_watchdog:
        _start_watchdog(project_dir)

    result = sm.run()

    status = result.get("status", "unknown")
    duration = result.get("duration_sec", "?")
    print(f"\nRun {result.get('run_id', '?')}: {status} ({duration}s)")
    return 0 if status == "completed" else 1


def cmd_resume(args):
    """Resume an existing research run."""
    from engine.state_machine import ResearchStateMachine

    project_dir = Path(args.project_dir).expanduser().resolve()
    state_file = project_dir / "run_state.json"

    if not state_file.exists():
        print(f"Error: No run_state.json found in {project_dir}", file=sys.stderr)
        return 1

    platform = args.platform or detect_platform()
    adapter = get_adapter(platform)

    sm = ResearchStateMachine(project_dir, adapter)
    sm.load_state()

    current = sm.state.get("current_state", "?")
    run_id = sm.state.get("run_id", "?")
    print(f"TrendR v2 — Resuming run {run_id} from {current}")

    # Reset status if it was paused/failed
    if sm.state.get("status") in ("paused", "failed"):
        sm.state["status"] = "running"
        sm.save_state()

    result = sm.run()

    status = result.get("status", "unknown")
    print(f"\nRun {run_id}: {status}")
    return 0 if status == "completed" else 1


def cmd_status(args):
    """Show status of a research run."""
    import json

    project_dir = Path(args.project_dir).expanduser().resolve()
    state_file = project_dir / "run_state.json"

    if not state_file.exists():
        print(f"No run_state.json in {project_dir}")
        return 1

    state = json.loads(state_file.read_text())
    print(f"Run:      {state.get('run_id', '?')}")
    print(f"Project:  {state.get('project', '?')}")
    print(f"Status:   {state.get('status', '?')}")
    print(f"State:    {state.get('current_state', '?')}")
    print(f"Platform: {state.get('platform', '?')}")
    print(f"Topic:    {state.get('params', {}).get('topic', '?')}")
    params = state.get("params", {})
    if params:
        print(
            "Discovery:"
            f" min={params.get('min_papers', '?')}"
            f" target={params.get('target_papers', params.get('min_papers', '?'))}"
            f" min_rounds={params.get('min_rounds', 1)}"
            f" max_rounds={params.get('max_rounds', '?')}"
        )
    print(f"Started:  {state.get('started_at', '?')}")

    # Show progress if available
    progress_file = project_dir / "progress.md"
    if progress_file.exists():
        print(f"\n{progress_file.read_text().strip()}")

    # Show history
    history = state.get("history", [])
    if history:
        print(f"\nHistory ({len(history)} entries):")
        for h in history:
            result = h.get("result", "...")
            metrics = h.get("metrics", "")
            metrics_str = f" {metrics}" if metrics else ""
            print(f"  {h['state']:12s} → {result}{metrics_str}")

    return 0


def _start_watchdog(project_dir: Path):
    """Start the watchdog as a background process."""
    import subprocess
    watchdog_script = Path(__file__).parent / "engine" / "watchdog.py"
    if not watchdog_script.exists():
        return

    try:
        proc = subprocess.Popen(
            [sys.executable, str(watchdog_script), str(project_dir)],
            stdout=open(project_dir / "logs" / "watchdog.out", "a"),
            stderr=subprocess.STDOUT,
        )
        pid_file = project_dir / "logs" / "watchdog.pid"
        pid_file.write_text(str(proc.pid))
        print(f"  Watchdog: PID {proc.pid}")
    except Exception as e:
        print(f"  Watchdog: failed to start ({e})")


def main():
    parser = argparse.ArgumentParser(
        prog="trendr",
        description="TrendR v2 — Research-agent harness system",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run
    run_parser = subparsers.add_parser("run", help="Start a new research run")
    run_parser.add_argument("--topic", "-t", required=True, help="Research topic")
    run_parser.add_argument("--depth", "-d", default="B", choices=["A", "B", "C"],
                           help="Depth: A=light, B=standard, C=deep")
    run_parser.add_argument("--platform", "-p", choices=["openclaw", "cli"],
                           help="Platform (auto-detected if omitted)")
    run_parser.add_argument("--project-dir", help="Custom project directory")
    run_parser.add_argument("--time-budget", type=int, default=60, help="Time budget in minutes")
    run_parser.add_argument("--min-papers", type=int, help="Minimum papers before DISCOVERY can advance")
    run_parser.add_argument("--target-papers", type=int, help="Preferred paper pool size before DISCOVERY exits")
    run_parser.add_argument("--min-rounds", type=int, help="Minimum DISCOVERY rounds before early exit")
    run_parser.add_argument("--max-rounds", type=int, help="Maximum DISCOVERY rounds before force-advance")
    run_parser.add_argument("--no-watchdog", action="store_true", help="Don't start watchdog")

    # resume
    resume_parser = subparsers.add_parser("resume", help="Resume an existing run")
    resume_parser.add_argument("project_dir", help="Project directory with run_state.json")
    resume_parser.add_argument("--platform", "-p", choices=["openclaw", "cli"])

    # status
    status_parser = subparsers.add_parser("status", help="Show run status")
    status_parser.add_argument("project_dir", help="Project directory")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "resume":
        sys.exit(cmd_resume(args))
    elif args.command == "status":
        sys.exit(cmd_status(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
