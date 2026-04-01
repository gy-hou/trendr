"""Platform-agnostic watchdog for the TrendR research state machine.

Monitors heartbeat.json + run_state.json to detect agent stalls.
On stall, writes resume_request.json for the platform adapter to handle.

No platform imports. No LLM calls. Pure filesystem polling.

See ARCHITECTURE.md §5 for the full specification.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("trendr.watchdog")


@dataclass
class WatchdogConfig:
    """Configuration for the watchdog daemon."""

    poll_sec: int = 60
    """How often to check heartbeat (seconds)."""

    idle_timeout_sec: int = 600
    """Max seconds without heartbeat before declaring stall."""

    phase_mismatch_grace_sec: int = 180
    """Grace period when artifacts suggest next phase but state hasn't advanced."""

    max_resume: int = 12
    """Maximum number of resume requests before giving up."""

    heartbeat_log_sec: int = 300
    """How often to write watchdog's own heartbeat to the log."""


@dataclass
class WatchdogState:
    """Internal state of the watchdog process."""

    stall_count: int = 0
    resume_count: int = 0
    last_heartbeat_seen: Optional[str] = None
    last_resume_at: Optional[str] = None
    started_at: str = field(default_factory=lambda: _now_iso())
    last_log_at: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    """Parse ISO timestamp, tolerant of trailing Z."""
    s = s.rstrip("Z")
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError:
        # Fallback: strip microseconds
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def _seconds_since(iso_str: str) -> float:
    """Seconds elapsed since the given ISO timestamp."""
    then = _parse_iso(iso_str)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds()


class Watchdog:
    """Platform-agnostic research pipeline watchdog.

    Usage:
        config = WatchdogConfig(poll_sec=60, idle_timeout_sec=600)
        wd = Watchdog(Path("~/research/my-project"), config)
        wd.run()  # blocks until pipeline completes or max_resume exceeded
    """

    def __init__(self, project_dir: Path, config: Optional[WatchdogConfig] = None):
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.config = config or WatchdogConfig()
        self.state = WatchdogState()
        self.logs_dir = self.project_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ── File paths ──────────────────────────────────────────────────

    @property
    def heartbeat_path(self) -> Path:
        return self.project_dir / "heartbeat.json"

    @property
    def run_state_path(self) -> Path:
        return self.project_dir / "run_state.json"

    @property
    def resume_request_path(self) -> Path:
        return self.project_dir / "resume_request.json"

    @property
    def watchdog_state_path(self) -> Path:
        return self.logs_dir / "watchdog_state.json"

    # ── Read helpers ────────────────────────────────────────────────

    def read_json(self, path: Path) -> Optional[dict]:
        """Read a JSON file, returning None on any error."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def read_run_state(self) -> Optional[dict]:
        return self.read_json(self.run_state_path)

    def read_heartbeat(self) -> Optional[dict]:
        return self.read_json(self.heartbeat_path)

    # ── Stall detection ─────────────────────────────────────────────

    def is_stalled(self, heartbeat: Optional[dict], run_state: Optional[dict]) -> bool:
        """Determine if the pipeline is stalled.

        Stall conditions:
        1. No heartbeat.json exists at all
        2. heartbeat.json.updated_at is older than idle_timeout_sec
        """
        if heartbeat is None:
            # No heartbeat file — could be early startup, check run_state age
            if run_state and "heartbeat_at" in run_state:
                age = _seconds_since(run_state["heartbeat_at"])
                return age > self.config.idle_timeout_sec
            return False  # Too early to tell

        updated_at = heartbeat.get("updated_at")
        if not updated_at:
            return True

        age = _seconds_since(updated_at)
        return age > self.config.idle_timeout_sec

    def is_pipeline_terminal(self, run_state: Optional[dict]) -> bool:
        """Check if the pipeline has reached a terminal state."""
        if run_state is None:
            return False
        return run_state.get("status") in ("completed", "failed")

    # ── Resume request ──────────────────────────────────────────────

    def write_resume_request(self, run_state: Optional[dict], heartbeat: Optional[dict]) -> None:
        """Write a resume_request.json for the platform adapter to pick up."""
        if self.state.resume_count >= self.config.max_resume:
            logger.warning(
                "Max resume attempts (%d) reached. Not writing resume request.",
                self.config.max_resume,
            )
            return

        current_state = run_state.get("current_state", "UNKNOWN") if run_state else "UNKNOWN"
        now = _now_iso()

        request = {
            "requested_at": now,
            "reason": self._stall_reason(heartbeat, run_state),
            "suggested_action": f"resume_{current_state.lower()}",
            "current_state": current_state,
            "stall_count": self.state.stall_count,
            "resume_count": self.state.resume_count + 1,
        }

        self.resume_request_path.write_text(
            json.dumps(request, indent=2), encoding="utf-8"
        )

        self.state.resume_count += 1
        self.state.last_resume_at = now
        self.save_state()

        logger.info(
            "Resume request #%d written: %s",
            self.state.resume_count,
            request["reason"],
        )

    def _stall_reason(self, heartbeat: Optional[dict], run_state: Optional[dict]) -> str:
        """Generate a human-readable stall reason."""
        if heartbeat is None:
            return "No heartbeat.json found"

        updated_at = heartbeat.get("updated_at", "unknown")
        if updated_at != "unknown":
            age = int(_seconds_since(updated_at))
            agent = heartbeat.get("agent", "unknown")
            state = heartbeat.get("state", "unknown")
            return (
                f"No heartbeat for {age}s (timeout={self.config.idle_timeout_sec}s) "
                f"in state {state} by agent {agent}"
            )

        return "Heartbeat file exists but has no updated_at"

    # ── State persistence ───────────────────────────────────────────

    def save_state(self) -> None:
        """Persist watchdog internal state for debugging."""
        data = {
            "stall_count": self.state.stall_count,
            "resume_count": self.state.resume_count,
            "last_heartbeat_seen": self.state.last_heartbeat_seen,
            "last_resume_at": self.state.last_resume_at,
            "started_at": self.state.started_at,
            "saved_at": _now_iso(),
        }
        self.watchdog_state_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    # ── Log heartbeat ───────────────────────────────────────────────

    def maybe_log_heartbeat(self) -> None:
        """Write the watchdog's own heartbeat entry to the log."""
        now = _now_iso()
        if self.state.last_log_at:
            elapsed = _seconds_since(self.state.last_log_at)
            if elapsed < self.config.heartbeat_log_sec:
                return

        run_state = self.read_run_state()
        current = run_state.get("current_state", "?") if run_state else "?"
        status = run_state.get("status", "?") if run_state else "?"

        log_line = (
            f"[{now}] watchdog heartbeat: "
            f"pipeline={status}/{current}, "
            f"stalls={self.state.stall_count}, "
            f"resumes={self.state.resume_count}\n"
        )

        log_file = self.logs_dir / "watchdog.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

        self.state.last_log_at = now

    # ── Main loop ───────────────────────────────────────────────────

    def run(self) -> dict:
        """Main watchdog loop. Blocks until pipeline completes or gives up.

        Returns:
            {"exit_reason": str, "stall_count": int, "resume_count": int}
        """
        logger.info(
            "Watchdog started for %s (poll=%ds, timeout=%ds, max_resume=%d)",
            self.project_dir,
            self.config.poll_sec,
            self.config.idle_timeout_sec,
            self.config.max_resume,
        )
        self.save_state()

        while True:
            run_state = self.read_run_state()

            # Terminal?
            if self.is_pipeline_terminal(run_state):
                status = run_state.get("status", "unknown") if run_state else "unknown"
                logger.info("Pipeline reached terminal state: %s", status)
                self.save_state()
                return {
                    "exit_reason": f"pipeline_{status}",
                    "stall_count": self.state.stall_count,
                    "resume_count": self.state.resume_count,
                }

            # Max resume exceeded?
            if self.state.resume_count >= self.config.max_resume:
                logger.error("Max resume attempts (%d) exceeded. Giving up.", self.config.max_resume)
                self.save_state()
                return {
                    "exit_reason": "max_resume_exceeded",
                    "stall_count": self.state.stall_count,
                    "resume_count": self.state.resume_count,
                }

            # Check heartbeat
            heartbeat = self.read_heartbeat()
            if heartbeat and heartbeat.get("updated_at"):
                self.state.last_heartbeat_seen = heartbeat["updated_at"]

            if self.is_stalled(heartbeat, run_state):
                self.state.stall_count += 1
                logger.warning(
                    "Stall #%d detected. Writing resume request.",
                    self.state.stall_count,
                )
                self.write_resume_request(run_state, heartbeat)

            # Watchdog's own heartbeat
            self.maybe_log_heartbeat()

            time.sleep(self.config.poll_sec)


# ── CLI entry point ─────────────────────────────────────────────────

def main():
    """Run the watchdog from the command line."""
    import argparse

    parser = argparse.ArgumentParser(description="TrendR v2 Watchdog")
    parser.add_argument("project_dir", help="Path to research project directory")
    parser.add_argument("--poll-sec", type=int, default=60)
    parser.add_argument("--idle-timeout-sec", type=int, default=600)
    parser.add_argument("--max-resume", type=int, default=12)
    parser.add_argument("--heartbeat-log-sec", type=int, default=300)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = WatchdogConfig(
        poll_sec=args.poll_sec,
        idle_timeout_sec=args.idle_timeout_sec,
        max_resume=args.max_resume,
        heartbeat_log_sec=args.heartbeat_log_sec,
    )

    wd = Watchdog(Path(args.project_dir), config)
    result = wd.run()
    logger.info("Watchdog exited: %s", result)


if __name__ == "__main__":
    main()
