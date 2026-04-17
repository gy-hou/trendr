#!/usr/bin/env python3
"""TrendR v2 — Research-agent harness CLI entry point.

Usage:
    python cli.py run --topic "RL multi-agent market making" --platform openclaw
    python cli.py run --topic "..." --platform codex
    python cli.py run --topic "..." --platform claude-code
    python cli.py run --topic "..." --platform cli
    python cli.py resume ~/research/my-project   # resume from run_state.json

See ARCHITECTURE.md for the full specification.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from engine.runtime import detect_runtime, normalize_runtime


DEPTH_PRESETS = {
    "A": {"min_papers": 20, "target_papers": 30, "min_rounds": 2, "max_rounds": 3},
    "B": {"min_papers": 30, "target_papers": 45, "min_rounds": 2, "max_rounds": 6},
    "C": {"min_papers": 50, "target_papers": 80, "min_rounds": 3, "max_rounds": 10},
}
PLATFORM_CHOICES = ["openclaw", "codex", "claude-code", "claudecode", "cli"]
PROFILE_CHOICES = ["lite", "basic", "full"]
HOTSPOTS_ALIASES = {"hotspots", "hot", "热点"}
RESEARCH_ALIASES = {"run", "research", "研究"}
TRENDR_OPENCLAW_AGENTS = ("paper-scout", "paper-analyzer", "review-lead", "verifier")


def detect_platform() -> str:
    """Auto-detect which platform we're running on."""
    return detect_runtime(os.environ)


def normalize_user_command_tokens(argv: list[str]) -> list[str]:
    """Normalize short slash-prefixed commands and multilingual aliases.

    Supported examples:
      /tr 热点
      /tr 研究
      /tr hot
      /tr research
    """
    tokens = list(argv or [])
    if not tokens:
        return tokens

    # Prefix compatibility: "/tr ...", "/ tr ...", "/trendr ..."
    first = tokens[0].strip().lower()
    if first in {"/tr", "/trendr"}:
        tokens = tokens[1:]
    elif len(tokens) >= 2 and tokens[0].strip() == "/" and tokens[1].strip().lower() in {"tr", "trendr"}:
        tokens = tokens[2:]

    if not tokens:
        return tokens

    cmd = tokens[0].strip()
    cmd_lower = cmd.lower()
    if cmd in HOTSPOTS_ALIASES or cmd_lower in HOTSPOTS_ALIASES:
        tokens[0] = "hotspots"
    elif cmd in RESEARCH_ALIASES or cmd_lower in RESEARCH_ALIASES:
        tokens[0] = "run"

    return tokens


def get_adapter(platform: str):
    """Instantiate the appropriate platform adapter."""
    platform_name = normalize_runtime(platform)
    if platform_name == "openclaw":
        from engine.adapters.openclaw import OpenClawAdapter
        return OpenClawAdapter(mode="cli")
    elif platform_name in {"codex", "claude-code", "cli"}:
        from engine.adapters.cli import CLIAdapter
        return CLIAdapter(repo_root=Path(__file__).parent, platform_name=platform_name)
    else:
        print(
            f"Error: Unknown platform '{platform}'. Available: {', '.join(PLATFORM_CHOICES)}",
            file=sys.stderr,
        )
        sys.exit(1)


def load_openclaw_config() -> dict | None:
    """Load the local OpenClaw config when present."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def validate_openclaw_agent_registry(config: dict | None = None) -> list[str]:
    """Return missing TrendR agent ids from the local OpenClaw registry."""
    data = config if config is not None else load_openclaw_config()
    if not isinstance(data, dict):
        return list(TRENDR_OPENCLAW_AGENTS)

    registered = {
        entry.get("id")
        for entry in data.get("agents", {}).get("list", [])
        if isinstance(entry, dict) and entry.get("id")
    }
    return sorted(agent for agent in TRENDR_OPENCLAW_AGENTS if agent not in registered)


def _extract_openclaw_primary_model(model_config) -> str:
    if isinstance(model_config, str):
        return model_config
    if isinstance(model_config, dict):
        primary = model_config.get("primary")
        if isinstance(primary, str):
            return primary
    return ""


def _resolve_openclaw_agent_primary_model(config: dict, agent_id: str) -> str:
    agents = {
        entry.get("id"): entry
        for entry in config.get("agents", {}).get("list", [])
        if isinstance(entry, dict) and entry.get("id")
    }
    agent_config = agents.get(agent_id, {})
    agent_model = _extract_openclaw_primary_model(agent_config.get("model"))
    if agent_model:
        return agent_model

    defaults = config.get("agents", {}).get("defaults", {})
    return _extract_openclaw_primary_model(defaults.get("model"))


def validate_openclaw_agent_auth(config: dict | None = None) -> list[str]:
    """Return auth-route mismatches for direct `openclaw agent` runs."""
    data = config if config is not None else load_openclaw_config()
    if not isinstance(data, dict):
        return []

    auth_profiles = data.get("auth", {}).get("profiles", {})
    configured_providers = {
        profile.get("provider")
        for profile in auth_profiles.values()
        if isinstance(profile, dict) and profile.get("provider")
    }
    issues: list[str] = []
    reported_models: set[str] = set()

    for agent_id in TRENDR_OPENCLAW_AGENTS:
        primary_model = _resolve_openclaw_agent_primary_model(data, agent_id)
        if not primary_model or "/" not in primary_model or primary_model in reported_models:
            continue
        provider = primary_model.split("/", 1)[0]
        if provider not in configured_providers:
            issues.append(
                f"Agent `{agent_id}` resolves to `{primary_model}`, but provider "
                f"`{provider}` has no auth profile in `~/.openclaw/openclaw.json`."
            )
            reported_models.add(primary_model)

    if issues and "auth" not in set(data.get("plugins", {}).get("allow", [])):
        issues.append(
            "OpenClaw auth plugin is disabled (`plugins.allow` excludes `auth`), "
            "so `openclaw auth login` is unavailable."
        )

    return issues


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


def update_local_research_history(project_dir: Path, state: dict) -> dict | None:
    """Persist a repo-local research history summary for recent runs."""
    from engine.research_history import update_research_history

    try:
        return update_research_history(
            repo_root=Path(__file__).parent,
            project_dir=project_dir,
            state=state,
            overflow_policy=os.environ.get("TRENDR_HISTORY_OVERFLOW", "prompt"),
            interactive=bool(sys.stdin.isatty() and sys.stdout.isatty()),
        )
    except Exception as exc:
        print(f"Warning: failed to update research history: {exc}", file=sys.stderr)
        return None


def cmd_run(args):
    """Start a new research run."""
    from engine.state_machine import ResearchStateMachine

    profile = (getattr(args, "profile", "basic") or "basic").lower()
    if profile == "lite":
        print(
            "Error: `run --profile lite` is not supported. "
            "Use `trendr hotspots` for the independent Lite flow.",
            file=sys.stderr,
        )
        return 2

    platform = normalize_runtime(args.platform) if args.platform else detect_platform()
    if platform == "openclaw":
        openclaw_config = load_openclaw_config()
        missing_agents = validate_openclaw_agent_registry(openclaw_config)
        if missing_agents:
            print(
                "Error: OpenClaw runtime is missing TrendR agents: "
                + ", ".join(missing_agents),
                file=sys.stderr,
            )
            print(
                "Fix: rerun `./install.sh` or register these agents in "
                "`~/.openclaw/openclaw.json`, then run `openclaw gateway restart`.",
                file=sys.stderr,
            )
            return 1
        auth_issues = validate_openclaw_agent_auth(openclaw_config)
        if auth_issues:
            print(
                "Error: OpenClaw runtime has provider/auth mismatches for direct TrendR agent runs:",
                file=sys.stderr,
            )
            for issue in auth_issues:
                print(f"  - {issue}", file=sys.stderr)
            print(
                "Fix: TrendR CLI mode uses direct `openclaw agent --agent ...` calls, "
                "so align `agents.defaults.model.primary` with a provider that has a "
                "working auth profile, or add auth for the current primary provider. "
                "If you change `~/.openclaw/openclaw.json`, run `openclaw gateway restart`.",
                file=sys.stderr,
            )
            return 1
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
    sm.state.setdefault("params", {})["profile"] = profile
    sm.save_state()

    print(f"TrendR v2 — Starting research run")
    print(f"  Topic:   {args.topic}")
    print(f"  Profile: {profile}")
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

    if result.get("status") == "completed" and profile == "full":
        from engine.hotspots_runner import HotspotsRunner

        print("\nFull profile: running post-run hotspots collection...")
        hotspots = HotspotsRunner(
            project_dir=project_dir,
            topic=args.topic,
            per_source_limit=max(1, int(getattr(args, "hotspots_limit", 10) or 10)),
            timeout_sec=max(5, int(getattr(args, "hotspots_timeout", 12) or 12)),
        ).run()
        print(
            "  Hotspots: "
            f"{hotspots.get('item_count', 0)} items, "
            f"{hotspots.get('sources_ok', 0)}/{hotspots.get('sources_total', 0)} sources OK"
        )

    status = result.get("status", "unknown")
    duration = result.get("duration_sec", "?")
    print(f"\nRun {result.get('run_id', '?')}: {status} ({duration}s)")
    history_result = update_local_research_history(project_dir, result)
    if history_result:
        print(
            "History: "
            f"{history_result['markdown_path']} "
            f"(records={history_result['record_count']}, action={history_result['action']})"
        )
    return 0 if status == "completed" else 1


def cmd_hotspots(args):
    """Run the independent TrendR Lite hotspot flow."""
    from engine.hotspots_runner import HotspotsRunner

    topic_value = (getattr(args, "topic", None) or "AI agents and LLM ecosystem").strip()

    if getattr(args, "project_dir", None):
        project_dir = Path(args.project_dir).expanduser().resolve()
    else:
        project_name = sanitize_project_name(topic_value)
        project_dir = Path.home() / "research" / f"{project_name}-hotspots"

    project_dir.mkdir(parents=True, exist_ok=True)

    runner = HotspotsRunner(
        project_dir=project_dir,
        topic=getattr(args, "topic", None),
        per_source_limit=getattr(args, "per_source_limit", 10),
        timeout_sec=getattr(args, "timeout_sec", 12),
        template_path=getattr(args, "template_path", None),
        private_path=getattr(args, "private_path", None),
        session_path=getattr(args, "session_path", None),
        use_private_config=not bool(getattr(args, "no_private_config", False)),
        auto_init_config=not bool(getattr(args, "no_auto_init", False)),
    )
    result = runner.run()

    print("TrendR Lite — Hotspots run")
    print(f"  Topic:    {topic_value}")
    print(f"  Profile:  lite")
    print(f"  Dir:      {project_dir}")
    print(
        "  Sources:  "
        f"{result.get('sources_ok', 0)}/{result.get('sources_total', 0)} OK"
    )
    print(f"  Items:    {result.get('item_count', 0)}")
    print(f"  Raw:      {result.get('raw_path')}")
    print(f"  Summary:  {result.get('summary_path')}")
    print(f"  Report:   {result.get('report_path')}")
    print(f"  Template: {result.get('template_path')}")
    print(f"  Private:  {result.get('private_path')}")
    print(f"  Session:  {result.get('session_path')}")
    print(f"  Reused Session: {bool(result.get('session_reused', False))}")

    return 0 if result.get("status") == "completed" else 1


def cmd_hotspots_template(args):
    """Generate shareable template + private user config skeleton."""
    from engine.hotspots_runner import write_hotspots_private_stub, write_hotspots_template

    template_path = Path(args.template_path).expanduser().resolve()
    private_path = Path(args.private_path).expanduser().resolve()

    write_hotspots_template(template_path, force=args.force)
    write_hotspots_private_stub(private_path, force=args.force)

    print("TrendR Lite — Hotspots template initialized")
    print(f"  Template: {template_path}")
    print(f"  Private:  {private_path}")
    print("  Note: keep private config out of public upload.")
    return 0


def cmd_resume(args):
    """Resume an existing research run."""
    from engine.state_machine import ResearchStateMachine

    project_dir = Path(args.project_dir).expanduser().resolve()
    state_file = project_dir / "run_state.json"

    if not state_file.exists():
        print(f"Error: No run_state.json found in {project_dir}", file=sys.stderr)
        return 1

    platform = normalize_runtime(args.platform) if args.platform else detect_platform()
    if platform == "openclaw":
        openclaw_config = load_openclaw_config()
        missing_agents = validate_openclaw_agent_registry(openclaw_config)
        if missing_agents:
            print(
                "Error: OpenClaw runtime is missing TrendR agents: "
                + ", ".join(missing_agents),
                file=sys.stderr,
            )
            print(
                "Fix: rerun `./install.sh` or register these agents in "
                "`~/.openclaw/openclaw.json`, then run `openclaw gateway restart`.",
                file=sys.stderr,
            )
            return 1
        auth_issues = validate_openclaw_agent_auth(openclaw_config)
        if auth_issues:
            print(
                "Error: OpenClaw runtime has provider/auth mismatches for direct TrendR agent runs:",
                file=sys.stderr,
            )
            for issue in auth_issues:
                print(f"  - {issue}", file=sys.stderr)
            print(
                "Fix: TrendR CLI mode uses direct `openclaw agent --agent ...` calls, "
                "so align `agents.defaults.model.primary` with a provider that has a "
                "working auth profile, or add auth for the current primary provider. "
                "If you change `~/.openclaw/openclaw.json`, run `openclaw gateway restart`.",
                file=sys.stderr,
            )
            return 1
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
    history_result = update_local_research_history(project_dir, result)
    if history_result:
        print(
            "History: "
            f"{history_result['markdown_path']} "
            f"(records={history_result['record_count']}, action={history_result['action']})"
        )
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
    print(f"Profile:  {state.get('params', {}).get('profile', 'basic')}")
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


def main(argv: list[str] | None = None):
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
    run_parser.add_argument(
        "--profile",
        default="basic",
        choices=PROFILE_CHOICES,
        help="Execution profile: basic/full (lite uses standalone `hotspots` command)",
    )
    run_parser.add_argument("--platform", "-p", choices=PLATFORM_CHOICES,
                           help="Platform (auto-detected if omitted)")
    run_parser.add_argument("--project-dir", help="Custom project directory")
    run_parser.add_argument("--time-budget", type=int, default=60, help="Time budget in minutes")
    run_parser.add_argument("--min-papers", type=int, help="Minimum papers before DISCOVERY can advance")
    run_parser.add_argument("--target-papers", type=int, help="Preferred paper pool size before DISCOVERY exits")
    run_parser.add_argument("--min-rounds", type=int, help="Minimum DISCOVERY rounds before early exit")
    run_parser.add_argument("--max-rounds", type=int, help="Maximum DISCOVERY rounds before force-advance")
    run_parser.add_argument("--hotspots-limit", type=int, default=10, help="Per-source hotspot item limit (full only)")
    run_parser.add_argument("--hotspots-timeout", type=int, default=12, help="Hotspots source timeout seconds (full only)")
    run_parser.add_argument("--no-watchdog", action="store_true", help="Don't start watchdog")

    # hotspots (independent Lite flow)
    hotspots_parser = subparsers.add_parser("hotspots", help="Run independent hotspots flow (Lite)")
    hotspots_parser.add_argument("--topic", "-t", help="Hotspot topic label (optional; defaults to template/private config)")
    hotspots_parser.add_argument("--project-dir", help="Custom project directory")
    hotspots_parser.add_argument("--per-source-limit", type=int, default=10, help="Max items per source")
    hotspots_parser.add_argument("--timeout-sec", type=int, default=12, help="Source timeout seconds")
    hotspots_parser.add_argument(
        "--template-path",
        default=str((Path.home() / ".trendr" / "hotspots" / "template.json")),
        help="Hotspots template JSON path",
    )
    hotspots_parser.add_argument(
        "--private-path",
        default=str((Path.home() / ".trendr" / "hotspots" / "private.json")),
        help="Private hotspots JSON path (user-only)",
    )
    hotspots_parser.add_argument(
        "--session-path",
        default=str((Path.home() / ".trendr" / "hotspots" / "session.json")),
        help="Session metadata JSON path",
    )
    hotspots_parser.add_argument("--no-private-config", action="store_true", help="Ignore private config for this run")
    hotspots_parser.add_argument("--no-auto-init", action="store_true", help="Do not auto-create template/private files")

    # hotspots template initializer
    hotspots_template_parser = subparsers.add_parser(
        "hotspots-template",
        help="Create hotspots template + private skeleton",
    )
    hotspots_template_parser.add_argument(
        "--template-path",
        default=str((Path.home() / ".trendr" / "hotspots" / "template.json")),
        help="Output path for shareable template JSON",
    )
    hotspots_template_parser.add_argument(
        "--private-path",
        default=str((Path.home() / ".trendr" / "hotspots" / "private.json")),
        help="Output path for private user JSON",
    )
    hotspots_template_parser.add_argument("--force", action="store_true", help="Overwrite existing files")

    # resume
    resume_parser = subparsers.add_parser("resume", help="Resume an existing run")
    resume_parser.add_argument("project_dir", help="Project directory with run_state.json")
    resume_parser.add_argument("--platform", "-p", choices=PLATFORM_CHOICES)

    # status
    status_parser = subparsers.add_parser("status", help="Show run status")
    status_parser.add_argument("project_dir", help="Project directory")

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    normalized_argv = normalize_user_command_tokens(raw_argv)
    args = parser.parse_args(normalized_argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "hotspots":
        sys.exit(cmd_hotspots(args))
    elif args.command == "hotspots-template":
        sys.exit(cmd_hotspots_template(args))
    elif args.command == "resume":
        sys.exit(cmd_resume(args))
    elif args.command == "status":
        sys.exit(cmd_status(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
