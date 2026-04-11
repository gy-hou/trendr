"""Research state machine for TrendR v2.

Pure Python, zero platform dependency. Reads run_state.json, checks transition
conditions via artifact validators, dispatches work via platform adapters.

See ARCHITECTURE.md §1 and §3 for the full specification.
"""

import json
import logging
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .adapters.base import PlatformAdapter
from .validators import ArtifactValidator, ValidationResult

logger = logging.getLogger("trendr.engine")


# ── Constants ───────────────────────────────────────────────────────

VALID_STATES = ("INIT", "DISCOVERY", "ANALYSIS", "GAP_CHECK", "WRITING", "VERIFY", "DONE")

STATE_AGENTS = {
    "INIT": "orchestrator",
    "DISCOVERY": "paper-scout",
    "ANALYSIS": "paper-analyzer",
    "GAP_CHECK": "orchestrator",
    "WRITING": "orchestrator",
    "VERIFY": "verifier",
    "DONE": "orchestrator",
}

# Default coverage threshold for GAP_CHECK → WRITING transition
DEFAULT_COVERAGE_THRESHOLD = 0.7

# Default max discovery rounds before forcing advancement
DEFAULT_MAX_DISCOVERY_ROUNDS = 6

# Default min discovery rounds before allowing early exit
DEFAULT_MIN_DISCOVERY_ROUNDS = 1

# Default max fix rounds (VERIFY → WRITING → VERIFY)
DEFAULT_MAX_FIX_ROUNDS = 2

# Agent timeouts per state
STATE_TIMEOUTS = {
    "INIT": 60,
    "DISCOVERY": 900,
    "ANALYSIS": 1200,
    "GAP_CHECK": 300,
    "WRITING": 1800,
    "VERIFY": 600,
    "DONE": 60,
}

DEFAULT_FALLBACK_ANALYSIS_ROWS = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    """Parse ISO timestamp, tolerant of trailing Z."""
    s = s.rstrip("Z")
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


# ── State Machine ───────────────────────────────────────────────────

class ResearchStateMachine:
    """Drives the TrendR research pipeline through well-defined states.

    Usage:
        adapter = OpenClawAdapter()
        sm = ResearchStateMachine(
            project_dir=Path("~/research/rl-market-making"),
            adapter=adapter,
        )
        sm.initialize(topic="RL multi-agent market making", depth="B")
        result = sm.run()
    """

    def __init__(self, project_dir: Path, adapter: PlatformAdapter):
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.adapter = adapter
        self.state: Optional[dict] = None
        self.validator = ArtifactValidator()

    # ── File paths ──────────────────────────────────────────────────

    @property
    def state_path(self) -> Path:
        return self.project_dir / "run_state.json"

    @property
    def candidates_path(self) -> Path:
        return self.project_dir / "candidates.csv"

    @property
    def search_log_path(self) -> Path:
        return self.project_dir / "search_log.md"

    @property
    def matrix_path(self) -> Path:
        return self.project_dir / "matrix.csv"

    @property
    def notes_dir(self) -> Path:
        return self.project_dir / "notes"

    @property
    def gap_report_path(self) -> Path:
        return self.project_dir / "gap_report.md"

    @property
    def review_path(self) -> Path:
        return self.project_dir / "review.md"

    @property
    def references_path(self) -> Path:
        return self.project_dir / "references.bib"

    @property
    def verify_path(self) -> Path:
        return self.project_dir / "verify.json"

    @property
    def progress_path(self) -> Path:
        return self.project_dir / "progress.md"

    @property
    def heartbeat_path(self) -> Path:
        return self.project_dir / "heartbeat.json"

    # ── State persistence ───────────────────────────────────────────

    def load_state(self) -> Optional[dict]:
        """Load run_state.json. Returns None if not found."""
        if self.state_path.exists():
            try:
                self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
                return self.state
            except json.JSONDecodeError:
                logger.error("Corrupt run_state.json")
                return None
        return None

    def save_state(self) -> None:
        """Persist current state to run_state.json."""
        self.state_path.write_text(
            json.dumps(self.state, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Initialization ──────────────────────────────────────────────

    def initialize(
        self,
        topic: str,
        depth: str = "B",
        min_papers: int = 30,
        target_papers: Optional[int] = None,
        min_rounds: int = DEFAULT_MIN_DISCOVERY_ROUNDS,
        max_rounds: int = DEFAULT_MAX_DISCOVERY_ROUNDS,
        time_budget_min: int = 60,
        run_id: Optional[str] = None,
    ) -> dict:
        """Create a new run_state.json and prepare the project directory.

        Args:
            topic: Research topic string
            depth: A (light) | B (standard) | C (deep)
            min_papers: Minimum papers for DISCOVERY exit
            target_papers: Preferred paper pool size before exiting DISCOVERY
            min_rounds: Minimum DISCOVERY rounds before allowing early exit
            max_rounds: Maximum DISCOVERY rounds before force-advance
            time_budget_min: Time budget in minutes
            run_id: Optional run ID (auto-generated if None)

        Returns:
            The initialized state dict.
        """
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        min_papers = max(1, int(min_papers))
        max_rounds = max(1, int(max_rounds))
        min_rounds = max(1, min(int(min_rounds), max_rounds))
        if target_papers is None:
            target_papers = min_papers
        target_papers = max(min_papers, int(target_papers))

        # Determine project name from directory
        project = self.project_dir.name

        # Create directory structure
        for subdir in ["notes", "logs", "papers"]:
            (self.project_dir / subdir).mkdir(parents=True, exist_ok=True)

        now = _now_iso()
        self.state = {
            "version": 2,
            "run_id": run_id,
            "project": project,
            "status": "running",
            "current_state": "INIT",
            "params": {
                "topic": topic,
                "min_papers": min_papers,
                "target_papers": target_papers,
                "min_rounds": min_rounds,
                "max_rounds": max_rounds,
                "depth": depth,
                "time_budget_min": time_budget_min,
            },
            "history": [
                {
                    "state": "INIT",
                    "entered_at": now,
                    "exited_at": None,
                    "agent": STATE_AGENTS["INIT"],
                    "result": None,
                }
            ],
            "discovery_rounds": 0,
            "fix_rounds": 0,
            "heartbeat_at": now,
            "started_at": now,
            "platform": self.adapter.platform_name,
        }

        self.save_state()

        # Write initial progress
        self._write_progress(0, "INIT", "Initializing research pipeline")

        # Write initial log
        log_path = self.project_dir / "logs" / f"{run_id}.log"
        log_content = (
            f"[{now}] TrendR v2 run started\n"
            f"  topic: {topic}\n"
            f"  depth: {depth}\n"
            f"  min_papers: {min_papers}\n"
            f"  target_papers: {target_papers}\n"
            f"  min_rounds: {min_rounds}\n"
            f"  max_rounds: {max_rounds}\n"
            f"  time_budget: {time_budget_min}min\n"
            f"  platform: {self.adapter.platform_name}\n"
        )
        log_path.write_text(log_content, encoding="utf-8")
        # Mirror to latest.log
        (self.project_dir / "logs" / "latest.log").write_text(log_content, encoding="utf-8")

        logger.info("Initialized run %s for topic: %s", run_id, topic)
        return self.state

    # ── Progress tracking ───────────────────────────────────────────

    PROGRESS_MAP = {
        "INIT": (0, 5),
        "DISCOVERY": (5, 40),
        "ANALYSIS": (40, 75),
        "GAP_CHECK": (75, 85),
        "WRITING": (85, 97),
        "VERIFY": (97, 99),
        "DONE": (100, 100),
    }

    def _write_progress(self, percent: int, phase: str, message: str) -> None:
        """Write human-readable progress.md."""
        filled = percent // 10
        bar = "#" * filled + "-" * (10 - filled)
        state_index = VALID_STATES.index(phase) if phase in VALID_STATES else 0
        content = f"[{bar}] {percent}% | Phase {state_index}/{len(VALID_STATES) - 1} | {message}\n"
        self.progress_path.write_text(content, encoding="utf-8")

    def _update_progress(self, phase: str, message: str, fraction: float = 0.0) -> None:
        """Update progress based on current phase and completion fraction within it."""
        lo, hi = self.PROGRESS_MAP.get(phase, (0, 100))
        percent = int(lo + (hi - lo) * min(max(fraction, 0.0), 1.0))
        self._write_progress(percent, phase, message)

    # ── Heartbeat ───────────────────────────────────────────────────

    def _send_heartbeat(self, message: str) -> None:
        """Write heartbeat.json and update state timestamp."""
        now = _now_iso()
        heartbeat = {
            "agent": STATE_AGENTS.get(self.state["current_state"], "unknown"),
            "state": self.state["current_state"],
            "updated_at": now,
            "message": message,
        }
        self.heartbeat_path.write_text(
            json.dumps(heartbeat, indent=2), encoding="utf-8"
        )
        self.state["heartbeat_at"] = now
        self.adapter.send_heartbeat(self.project_dir, heartbeat)

    # ── Logging ─────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        """Append to the run log and mirror to latest.log."""
        now = _now_iso()
        line = f"[{now}] {message}\n"
        run_id = self.state.get("run_id", "unknown")
        log_path = self.project_dir / "logs" / f"{run_id}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        # Mirror
        latest = self.project_dir / "logs" / "latest.log"
        with open(latest, "a", encoding="utf-8") as f:
            f.write(line)
        logger.info(message)

    # ── Transition logic ────────────────────────────────────────────

    def transition(self, next_state: str, result: str = "ok", metrics: Optional[dict] = None) -> None:
        """Record a state transition."""
        now = _now_iso()

        # Close current history entry
        if self.state["history"]:
            last = self.state["history"][-1]
            if last["exited_at"] is None:
                last["exited_at"] = now
                last["result"] = result
                if metrics:
                    last["metrics"] = metrics

        # Open new history entry
        self.state["history"].append({
            "state": next_state,
            "entered_at": now,
            "exited_at": None,
            "agent": STATE_AGENTS.get(next_state, "unknown"),
            "result": None,
        })

        old_state = self.state["current_state"]
        self.state["current_state"] = next_state
        self.state["heartbeat_at"] = now
        self.save_state()

        self._log(f"Transition: {old_state} → {next_state} (result={result})")
        self._update_progress(next_state, f"Entering {next_state}", 0.0)

    def check_transition(self) -> Optional[str]:
        """Check if the current state's exit conditions are met.

        Returns:
            Next state name, or None if conditions not met.
        """
        current = self.state["current_state"]
        checkers = {
            "INIT": self._check_init_exit,
            "DISCOVERY": self._check_discovery_exit,
            "ANALYSIS": self._check_analysis_exit,
            "GAP_CHECK": self._check_gap_exit,
            "WRITING": self._check_writing_exit,
            "VERIFY": self._check_verify_exit,
        }
        checker = checkers.get(current)
        if checker:
            return checker()
        return None

    def _check_init_exit(self) -> Optional[str]:
        """INIT exits when run_state.json is valid and status is running."""
        result = self.validator.validate_run_state(self.state_path)
        if result and self.state.get("status") == "running":
            return "DISCOVERY"
        return None

    def _get_discovery_params(self) -> tuple[int, int, int, int]:
        """Return normalized DISCOVERY thresholds from run parameters."""
        params = self.state.get("params", {})
        min_papers = max(1, int(params.get("min_papers", 20)))
        max_rounds = max(1, int(params.get("max_rounds", DEFAULT_MAX_DISCOVERY_ROUNDS)))
        min_rounds = max(1, min(int(params.get("min_rounds", DEFAULT_MIN_DISCOVERY_ROUNDS)), max_rounds))
        target_papers = max(min_papers, int(params.get("target_papers", min_papers)))
        return min_papers, target_papers, min_rounds, max_rounds

    def _check_discovery_exit(self) -> Optional[str]:
        """DISCOVERY exits after minimum rounds and target paper pool are satisfied."""
        min_papers, target_papers, min_rounds, max_rounds = self._get_discovery_params()
        discovery_rounds = self.state.get("discovery_rounds", 0)
        result = self.validator.validate_candidates_csv(self.candidates_path, min_rows=0)

        if not result:
            if discovery_rounds < max_rounds:
                self._log(
                    f"Discovery round {discovery_rounds}/{max_rounds} candidates not ready "
                    f"({result.message}). Continuing discovery."
                )
                return "DISCOVERY"
            return None

        row_count = int((result.details or {}).get("row_count", 0))

        if discovery_rounds < min_rounds:
            if discovery_rounds < max_rounds:
                self._log(
                    f"Discovery round {discovery_rounds}/{max_rounds} found {row_count} papers, "
                    f"but min_rounds={min_rounds} not met. Continuing discovery."
                )
                return "DISCOVERY"
            if row_count >= 1:
                self._log(
                    f"Discovery rounds exhausted ({max_rounds}) before min_rounds could be satisfied. "
                    f"Advancing with available papers ({row_count})."
                )
                return "ANALYSIS"
            return None

        if row_count >= target_papers:
            return "ANALYSIS"

        if discovery_rounds < max_rounds:
            if row_count >= min_papers:
                self._log(
                    f"Discovery round {discovery_rounds}/{max_rounds} met min_papers ({min_papers}) "
                    f"with {row_count} papers, but target_papers ({target_papers}) not reached. "
                    f"Continuing discovery."
                )
            else:
                self._log(
                    f"Discovery round {discovery_rounds}/{max_rounds} below min_papers "
                    f"({min_papers}); current row_count={row_count}. Continuing discovery."
                )
            return "DISCOVERY"

        if row_count >= 1:
            if row_count >= min_papers:
                self._log(
                    f"Discovery rounds exhausted ({max_rounds}) before target_papers ({target_papers}) "
                    f"was reached. Advancing with available papers ({row_count})."
                )
            else:
                self._log(
                    f"Discovery rounds exhausted ({max_rounds}) below min_papers ({min_papers}). "
                    f"Advancing with available papers ({row_count})."
                )
            return "ANALYSIS"
        return None

    def _check_analysis_exit(self) -> Optional[str]:
        """ANALYSIS exits when matrix.csv and enough notes exist."""
        matrix_result = self.validator.validate_matrix_csv(self.matrix_path, self.candidates_path)
        if not matrix_result:
            return None

        # Count papers with relevance >= 4 to determine minimum notes needed
        notes_result = self.validator.validate_notes_dir(self.notes_dir, min_count=1)
        if not notes_result:
            return None

        return "GAP_CHECK"

    def _check_gap_exit(self) -> Optional[str]:
        """GAP_CHECK exits based on coverage_score vs threshold."""
        result = self.validator.validate_gap_report(self.gap_report_path)
        if not result:
            return None

        score = self.validator.get_coverage_score(self.gap_report_path)
        if score is None:
            return None

        max_rounds = self.state.get("params", {}).get("max_rounds", DEFAULT_MAX_DISCOVERY_ROUNDS)
        discovery_rounds = self.state.get("discovery_rounds", 0)

        if score >= DEFAULT_COVERAGE_THRESHOLD:
            return "WRITING"
        elif self.state.get("budget_exceeded"):
            self._log(
                f"Coverage {score:.2f} below threshold but budget is exceeded. "
                "Advancing to WRITING in soft-budget mode."
            )
            return "WRITING"
        elif discovery_rounds >= max_rounds:
            self._log(f"Coverage {score:.2f} below threshold but max rounds reached. Advancing.")
            return "WRITING"
        else:
            # Loop back to DISCOVERY
            self._log(f"Coverage {score:.2f} below threshold. Looping back to DISCOVERY.")
            self.state["discovery_rounds"] = discovery_rounds + 1
            self.save_state()
            return "DISCOVERY"

    def _check_writing_exit(self) -> Optional[str]:
        """WRITING exits when review.md and references.bib pass validation."""
        review_result = self.validator.validate_review_md(self.review_path)
        if not review_result:
            return None

        bib_result = self.validator.validate_references_bib(self.references_path, self.review_path)
        if not bib_result:
            return None

        return "VERIFY"

    def _check_verify_exit(self) -> Optional[str]:
        """VERIFY exits based on verify.json pass/fail."""
        result = self.validator.validate_verify_json(self.verify_path)
        if not result:
            return None

        passed = self.validator.get_verify_pass(self.verify_path)
        if passed is True:
            return "DONE"

        # Fix loop
        fix_rounds = self.state.get("fix_rounds", 0)
        if fix_rounds >= DEFAULT_MAX_FIX_ROUNDS:
            self._log(f"Max fix rounds ({DEFAULT_MAX_FIX_ROUNDS}) reached. Accepting with issues.")
            return "DONE"

        self._log(f"Verification failed. Fix round {fix_rounds + 1}/{DEFAULT_MAX_FIX_ROUNDS}.")
        self.state["fix_rounds"] = fix_rounds + 1
        self.save_state()
        return "WRITING"

    # ── State executors ─────────────────────────────────────────────

    def execute_current(self) -> bool:
        """Execute the current state's work via the adapter.

        Returns:
            True if execution succeeded and we should check transitions.
            False if execution failed (state machine will mark as failed).
        """
        current = self.state["current_state"]
        executors = {
            "INIT": self._exec_init,
            "DISCOVERY": self._exec_discovery,
            "ANALYSIS": self._exec_analysis,
            "GAP_CHECK": self._exec_gap_check,
            "WRITING": self._exec_writing,
            "VERIFY": self._exec_verify,
            "DONE": self._exec_done,
        }
        executor = executors.get(current)
        if not executor:
            self._log(f"No executor for state: {current}")
            return False

        self._send_heartbeat(f"Executing {current}")
        self._log(f"Executing state: {current}")

        try:
            return executor()
        except Exception as e:
            self._log(f"Exception in {current}: {e}")
            logger.exception("Error executing %s", current)
            return False

    def _exec_init(self) -> bool:
        """INIT: directories and state file already created by initialize(). Just advance."""
        self._update_progress("INIT", "Initialization complete", 1.0)
        return True

    def _exec_discovery(self) -> bool:
        """DISCOVERY: dispatch paper-scout to search for papers."""
        topic = self.state["params"]["topic"]
        depth = self.state["params"]["depth"]
        project_dir = str(self.project_dir)
        round_num = self.state.get("discovery_rounds", 0) + 1
        min_papers, target_papers, min_rounds, max_rounds = self._get_discovery_params()

        task = (
            f"Read skills/paper-scout/SKILL.md, then search for papers on: {topic}. "
            f"Project directory: {project_dir}. "
            f"Depth level: {depth}. Discovery round: {round_num}/{max_rounds}. "
            f"Minimum papers: {min_papers}. Target papers: {target_papers}. "
            f"Minimum discovery rounds before exit: {min_rounds}. "
            f"Output candidates.csv and search_log.md to the project directory. "
            f"If candidates.csv already exists, merge new results and keep expanding coverage; "
            f"do not stop just because the minimum threshold has been met. "
            f"If web_fetch fails with private/internal IP error, switch to "
            f"arxiv-watcher + Chrome CDP browser + tavily-search + web_search fallback. "
            f"If browser fallback is needed, first check Chrome CDP: "
            f"run 'curl -fsS http://127.0.0.1:19222/json/version'. "
            f"If not running, run 'bash scripts/start-chrome-cdp.sh' or "
            f"'bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh'. "
            f"Use --browser-profile cdp (not garry)."
        )

        self._update_progress("DISCOVERY", f"Scout searching (round {round_num})", 0.2)
        handle = self.adapter.spawn_agent("paper-scout", task, STATE_TIMEOUTS["DISCOVERY"])

        self._send_heartbeat(f"Discovery round {round_num}: scout dispatched")
        result = self.adapter.await_agent(handle)

        self._update_progress("DISCOVERY", f"Scout returned: {result.get('status', '?')}", 0.9)
        self.state["discovery_rounds"] = round_num
        self.save_state()

        return result.get("status") == "completed"

    def _exec_analysis(self) -> bool:
        """ANALYSIS: dispatch paper-analyzer to analyze discovered papers."""
        project_dir = str(self.project_dir)

        task = (
            f"Read skills/paper-analyzer/SKILL.md, then analyze papers from "
            f"{project_dir}/candidates.csv (relevance_score >= 4). "
            f"Write notes to {project_dir}/notes/ and matrix.csv to {project_dir}/."
        )

        self._update_progress("ANALYSIS", "Analyzer working", 0.2)
        handle = self.adapter.spawn_agent("paper-analyzer", task, STATE_TIMEOUTS["ANALYSIS"])

        self._send_heartbeat("Analysis: analyzer dispatched")
        result = self.adapter.await_agent(handle)

        self._update_progress("ANALYSIS", f"Analyzer returned: {result.get('status', '?')}", 0.9)
        analyzer_completed = result.get("status") == "completed"

        matrix_result = self.validator.validate_matrix_csv(self.matrix_path, self.candidates_path)
        notes_result = self.validator.validate_notes_dir(self.notes_dir, min_count=1)
        artifacts_ready = bool(matrix_result and notes_result)

        if analyzer_completed and artifacts_ready:
            return True

        fallback_reason = (
            "analyzer did not complete"
            if not analyzer_completed
            else "analysis artifacts missing or invalid"
        )
        self._log(
            "ANALYSIS fallback triggered: "
            f"{fallback_reason}. Generating minimal notes/matrix."
        )
        return self._write_minimal_analysis_artifacts(reason=fallback_reason)

    def _exec_gap_check(self) -> bool:
        """GAP_CHECK: orchestrator reads all artifacts and produces gap_report.md.

        For OpenClaw, this is dispatched to review-lead.
        The gap report must contain a coverage_score: line.
        """
        project_dir = str(self.project_dir)

        task = (
            f"Read all notes in {project_dir}/notes/, matrix.csv, and candidates.csv. "
            f"Identify coverage gaps: which sub-topics are underrepresented? "
            f"Which methodological categories need more papers? "
            f"Write gap_report.md to {project_dir}/. "
            f"The report MUST contain a line: coverage_score: X.XX (0.0-1.0). "
            f"Score guidelines: 0.9+ = excellent coverage, 0.7-0.9 = adequate, <0.7 = gaps exist."
        )

        self._update_progress("GAP_CHECK", "Checking coverage gaps", 0.3)
        handle = self.adapter.spawn_agent("review-lead", task, STATE_TIMEOUTS["GAP_CHECK"])

        self._send_heartbeat("Gap check in progress")
        result = self.adapter.await_agent(handle)

        self._update_progress("GAP_CHECK", f"Gap check: {result.get('status', '?')}", 0.9)
        return result.get("status") == "completed"

    def _exec_writing(self) -> bool:
        """WRITING: orchestrator writes the literature review."""
        project_dir = str(self.project_dir)
        topic = self.state["params"]["topic"]
        fix_round = self.state.get("fix_rounds", 0)

        fix_instruction = ""
        if fix_round > 0 and self.verify_path.exists():
            fix_instruction = (
                f" This is fix round {fix_round}. Read {project_dir}/verify.json "
                f"and fix all issues marked as errors."
            )

        task = (
            f"Read skills/review-writer/SKILL.md. "
            f"Write a literature review on: {topic}. "
            f"Read all notes from {project_dir}/notes/, matrix.csv, candidates.csv, "
            f"and gap_report.md. "
            f"Output review.md and references.bib to {project_dir}/.{fix_instruction}"
        )

        self._update_progress("WRITING", f"Writing review (fix={fix_round})", 0.2)
        handle = self.adapter.spawn_agent("review-lead", task, STATE_TIMEOUTS["WRITING"])

        self._send_heartbeat(f"Writing review (fix round {fix_round})")
        result = self.adapter.await_agent(handle)

        self._update_progress("WRITING", f"Writing: {result.get('status', '?')}", 0.9)
        return result.get("status") == "completed"

    def _exec_verify(self) -> bool:
        """VERIFY: dispatch verifier agent."""
        project_dir = str(self.project_dir)
        run_id = self.state.get("run_id", "unknown")

        task = (
            f"Read skills/verifier/SKILL.md. "
            f"Verify the literature review at {project_dir}/. "
            f"Read review.md, references.bib, candidates.csv, matrix.csv, and all notes/*.md. "
            f"Run all 6 checks and output verify.json to {project_dir}/. "
            f"Set run_id to {run_id}."
        )

        self._update_progress("VERIFY", "Verifier running", 0.3)
        handle = self.adapter.spawn_agent("verifier", task, STATE_TIMEOUTS["VERIFY"])

        self._send_heartbeat("Verification in progress")
        result = self.adapter.await_agent(handle)

        self._update_progress("VERIFY", f"Verify: {result.get('status', '?')}", 0.9)
        if result.get("status") != "completed":
            return False

        return self._write_deterministic_verify(run_id=run_id)

    def _exec_done(self) -> bool:
        """DONE: finalize the run."""
        now = _now_iso()
        self.state["status"] = "completed"
        self.state["finished_at"] = now

        # Calculate duration
        started = self.state.get("started_at", now)
        try:
            start_dt = _parse_iso(started)
            end_dt = _parse_iso(now)
            self.state["duration_sec"] = int((end_dt - start_dt).total_seconds())
        except Exception:
            self.state["duration_sec"] = 0

        self.save_state()
        self._update_progress("DONE", "Research complete", 1.0)
        self._log(f"Run completed. Duration: {self.state.get('duration_sec', '?')}s")
        return True

    # ── Resume support ──────────────────────────────────────────────

    def check_resume_request(self) -> Optional[dict]:
        """Check if the watchdog has written a resume_request.json."""
        resume_path = self.project_dir / "resume_request.json"
        if not resume_path.exists():
            return None
        try:
            request = json.loads(resume_path.read_text(encoding="utf-8"))
            # Consume the request by deleting it
            resume_path.unlink()
            self._log(f"Consumed resume request: {request.get('reason', '?')}")
            return request
        except (json.JSONDecodeError, OSError):
            return None

    def _budget_status(self) -> tuple[int, int]:
        """Return elapsed seconds and configured budget seconds."""
        budget_min = int(self.state.get("params", {}).get("time_budget_min", 0) or 0)
        budget_sec = max(0, budget_min * 60)
        started_at = self.state.get("started_at")
        if not started_at:
            return 0, budget_sec

        try:
            started_dt = _parse_iso(started_at)
        except Exception:
            return 0, budget_sec

        elapsed_sec = max(0, int((datetime.now(timezone.utc) - started_dt).total_seconds()))
        return elapsed_sec, budget_sec

    def _update_budget_flag(self) -> None:
        """Mark budget_exceeded once without hard force-advancing states."""
        current = self.state["current_state"]
        if current in ("WRITING", "VERIFY", "DONE"):
            return

        elapsed_sec, budget_sec = self._budget_status()
        if elapsed_sec < budget_sec:
            return

        if not self.state.get("budget_exceeded"):
            self.state["budget_exceeded"] = True
            self.save_state()
            self._log(
                f"Budget exceeded ({elapsed_sec}s > {budget_sec}s). "
                "Switching to soft-budget mode (no hard state skipping)."
            )

    def _transition_validation_results(self, state: str) -> list[ValidationResult]:
        """Collect the validators relevant to a state's exit conditions."""
        results: list[ValidationResult] = []

        if state == "INIT":
            results.append(self.validator.validate_run_state(self.state_path))
            if self.state.get("status") != "running":
                results.append(
                    ValidationResult(
                        False,
                        f"run_state status is {self.state.get('status')} (expected running)",
                        {"status": self.state.get("status")},
                    )
                )
        elif state == "DISCOVERY":
            min_papers = self.state.get("params", {}).get("min_papers", 20)
            results.append(self.validator.validate_candidates_csv(self.candidates_path, min_rows=min_papers))
            max_rounds = self.state.get("params", {}).get("max_rounds", DEFAULT_MAX_DISCOVERY_ROUNDS)
            if self.state.get("discovery_rounds", 0) >= max_rounds:
                results.append(self.validator.validate_candidates_csv(self.candidates_path, min_rows=1))
        elif state == "ANALYSIS":
            results.append(self.validator.validate_matrix_csv(self.matrix_path, self.candidates_path))
            results.append(self.validator.validate_notes_dir(self.notes_dir, min_count=1))
        elif state == "GAP_CHECK":
            gap_result = self.validator.validate_gap_report(self.gap_report_path)
            results.append(gap_result)
            if gap_result:
                score = self.validator.get_coverage_score(self.gap_report_path)
                if score is None:
                    results.append(
                        ValidationResult(
                            False,
                            "gap_report.md missing valid coverage_score",
                        )
                    )
        elif state == "WRITING":
            results.append(self.validator.validate_review_md(self.review_path))
            results.append(self.validator.validate_references_bib(self.references_path, self.review_path))
        elif state == "VERIFY":
            verify_result = self.validator.validate_verify_json(self.verify_path)
            results.append(verify_result)
            if verify_result:
                passed = self.validator.get_verify_pass(self.verify_path)
                if passed is None:
                    results.append(
                        ValidationResult(
                            False,
                            "verify.json missing boolean pass field",
                        )
                    )

        return [result for result in results if not result]

    def _log_transition_failure(self) -> None:
        """Record validator failures for the current state's transition."""
        current = self.state["current_state"]
        failures = self._transition_validation_results(current)
        if not failures:
            return

        seen: set[tuple[str, str]] = set()
        error_entries = []
        for result in failures:
            detail_text = json.dumps(result.details, sort_keys=True, ensure_ascii=False)
            key = (result.message, detail_text)
            if key in seen:
                continue
            seen.add(key)

            self._log(f" Validator failed: {result.message}")
            if result.details:
                self._log(f" Details: {result.details}")

            entry = {"message": result.message}
            if result.details:
                entry["details"] = result.details
            error_entries.append(entry)

        if not error_entries or not self.state.get("history"):
            return

        history_entry = self.state["history"][-1]
        existing = history_entry.setdefault("validation_errors", [])
        existing.extend(error_entries)
        self.save_state()

    # ── Main loop ───────────────────────────────────────────────────

    def run(self) -> dict:
        """Main execution loop. Blocks until DONE or failure.

        Returns:
            Final run_state dict.
        """
        if self.state is None:
            loaded = self.load_state()
            if loaded is None:
                raise RuntimeError("No run_state.json found. Call initialize() first.")

        self._log(f"State machine starting from {self.state['current_state']}")

        while self.state["current_state"] != "DONE" and self.state["status"] == "running":
            current = self.state["current_state"]
            self._update_budget_flag()

            # Execute current state
            success = self.execute_current()

            if not success:
                # Check if we got a resume request (watchdog intervention)
                resume = self.check_resume_request()
                if resume:
                    self._log(f"Retrying {current} after resume request")
                    continue

                self._log(f"State {current} failed. Marking run as failed.")
                self.state["status"] = "failed"
                self.state["finished_at"] = _now_iso()
                self.save_state()
                break

            # Check transition
            next_state = self.check_transition()
            if next_state:
                metrics = self._collect_metrics(current)
                self.transition(next_state, result="ok", metrics=metrics)

                if next_state == "DONE":
                    self.execute_current()  # finalize
            else:
                # No transition possible — execution succeeded but artifacts not ready
                self._log_transition_failure()
                self._log(f"State {current} executed but transition conditions not met")
                self.state["status"] = "failed"
                self.state["finished_at"] = _now_iso()
                self.save_state()
                break

        return self.state

    def _select_fallback_analysis_rows(self) -> list[dict]:
        """Select candidate rows for minimal analysis fallback outputs."""
        if not self.candidates_path.exists():
            return []

        try:
            text = self.candidates_path.read_text(encoding="utf-8")
        except Exception:
            return []

        rows = list(csv.DictReader(text.splitlines()))
        if not rows:
            return []

        scored_rows: list[tuple[float, dict]] = []
        for row in rows:
            paper_id = (row.get("paper_id") or "").strip()
            if not paper_id:
                continue
            try:
                score = float((row.get("relevance_score") or "0").strip() or 0)
            except ValueError:
                score = 0.0
            scored_rows.append((score, row))

        if not scored_rows:
            return []

        high_rel = [item for item in scored_rows if item[0] >= 4.0]
        selected = high_rel if high_rel else scored_rows
        selected.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in selected[:DEFAULT_FALLBACK_ANALYSIS_ROWS]]

    def _safe_note_stem(self, paper_id: str) -> str:
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", paper_id).strip("._-")
        return stem or "paper"

    def _write_minimal_analysis_artifacts(self, reason: str) -> bool:
        """Create minimal valid notes/matrix when analyzer output is missing."""
        rows = self._select_fallback_analysis_rows()
        if not rows:
            self._log(
                "ANALYSIS fallback failed: candidates.csv unavailable or empty; "
                "cannot synthesize minimal notes/matrix."
            )
            return False

        self.notes_dir.mkdir(parents=True, exist_ok=True)
        created_notes = 0

        for row in rows:
            paper_id = (row.get("paper_id") or "").strip() or "unknown"
            title = (row.get("title") or "").strip() or "N/A"
            authors = (row.get("authors") or "").strip() or "N/A"
            year = (row.get("year") or "").strip() or "N/A"
            source = (row.get("source") or "").strip() or "N/A"
            score_raw = (row.get("relevance_score") or "0").strip() or "0"
            safe_title = title.replace('"', "'")
            safe_authors = authors.replace('"', "'")
            note_path = self.notes_dir / f"fallback_{self._safe_note_stem(paper_id)}.md"

            if note_path.exists():
                continue

            note_content = (
                "---\n"
                f"paper_id: \"{paper_id}\"\n"
                f"title: \"{safe_title}\"\n"
                f"relevance_score: {score_raw}\n"
                f"year: {year}\n"
                f"source: \"{source}\"\n"
                f"authors: \"{safe_authors}\"\n"
                "venue: \"N/A\"\n"
                "citation_count: 0\n"
                "retrieval_status: \"ACCESS_FAILED\"\n"
                "---\n\n"
                "## Summary\n"
                f"Fallback note generated by state machine because ANALYSIS was incomplete ({reason}).\n\n"
                "## Research Question\n"
                "N/A\n\n"
                "## Methodology\n"
                "N/A\n\n"
                "## Key Findings\n"
                "| Metric | Dataset | Value | Baseline |\n"
                "|--------|---------|-------|----------|\n"
                "| N/A | N/A | N/A | N/A |\n\n"
                "## Contributions\n"
                "1. N/A\n\n"
                "## Limitations\n"
                "- Full-text analysis unavailable in fallback mode.\n\n"
                "## Key Citations\n"
                "- N/A\n\n"
                "## Tags\n"
                "fallback-analysis\n\n"
                "## BibTeX\n"
                "```bibtex\n"
                f"@misc{{{paper_id},\n"
                f"  title={{{title}}},\n"
                f"  author={{{authors}}},\n"
                f"  year={{{year}}}\n"
                "}\n"
                "```\n"
            )
            note_path.write_text(note_content, encoding="utf-8")
            created_notes += 1

        matrix_rows = []
        for row in rows:
            matrix_rows.append(
                {
                    "paper_id": (row.get("paper_id") or "").strip() or "unknown",
                    "title": (row.get("title") or "").strip() or "N/A",
                    "year": (row.get("year") or "").strip() or "N/A",
                    "method": "N/A",
                    "dataset": "N/A",
                    "metric": "N/A",
                    "result": "N/A",
                    "category": "fallback",
                    "strengths": "N/A",
                    "limitations": "Generated by fallback; full analysis missing",
                }
            )

        fieldnames = [
            "paper_id", "title", "year", "method", "dataset",
            "metric", "result", "category", "strengths", "limitations",
        ]
        with open(self.matrix_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matrix_rows)

        matrix_result = self.validator.validate_matrix_csv(self.matrix_path, self.candidates_path)
        notes_result = self.validator.validate_notes_dir(self.notes_dir, min_count=1)
        ok = bool(matrix_result and notes_result)

        self._log(
            "ANALYSIS fallback artifacts written: "
            f"notes_created={created_notes}, matrix_rows={len(matrix_rows)}, valid={ok}"
        )
        if not ok:
            if not matrix_result:
                self._log(f"ANALYSIS fallback matrix validation failed: {matrix_result.message}")
            if not notes_result:
                self._log(f"ANALYSIS fallback notes validation failed: {notes_result.message}")
        return ok

    def _write_deterministic_verify(self, run_id: str) -> bool:
        """Generate verify.json via local deterministic checks."""
        try:
            from .verifier import run_all_checks
        except Exception as e:
            self._log(f"Failed to import local verifier: {e}")
            return False

        verify_payload = run_all_checks(
            review_path=self.review_path,
            bib_path=self.references_path,
            candidates_path=self.candidates_path,
            notes_dir=self.notes_dir,
            run_id=run_id,
            api_check=False,
        )
        self.verify_path.write_text(
            json.dumps(verify_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._log(
            "[local-verifier] verify.json generated: "
            f"pass={verify_payload.get('pass')} summary={verify_payload.get('summary')}"
        )
        return True

    def _collect_metrics(self, state: str) -> Optional[dict]:
        """Collect metrics for the completed state's history entry."""
        if state == "DISCOVERY":
            result = self.validator.validate_candidates_csv(self.candidates_path, min_rows=0)
            if result:
                return result.details
        elif state == "ANALYSIS":
            notes = list(self.notes_dir.glob("*.md")) if self.notes_dir.exists() else []
            return {"notes_count": len(notes)}
        elif state == "GAP_CHECK":
            score = self.validator.get_coverage_score(self.gap_report_path)
            if score is not None:
                return {"coverage_score": score}
        elif state == "VERIFY":
            passed = self.validator.get_verify_pass(self.verify_path)
            if passed is not None:
                return {"pass": passed}
        return None
