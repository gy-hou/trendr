import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from engine.watchdog import Watchdog, WatchdogConfig


class WatchdogTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_watchdog(self, **config_kwargs) -> Watchdog:
        project_dir = self.root / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        config = WatchdogConfig(**config_kwargs)
        return Watchdog(project_dir, config)

    def write_json(self, path: Path, data: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def iso_ago(self, seconds: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_is_stalled_without_heartbeat(self) -> None:
        wd = self.make_watchdog(idle_timeout_sec=10)
        run_state = {"heartbeat_at": self.iso_ago(30)}

        self.assertTrue(wd.is_stalled(None, run_state))

    def test_is_stalled_when_heartbeat_expired(self) -> None:
        wd = self.make_watchdog(idle_timeout_sec=10)
        heartbeat = {"updated_at": self.iso_ago(30), "agent": "paper-scout", "state": "DISCOVERY"}

        self.assertTrue(wd.is_stalled(heartbeat, {"status": "running"}))

    def test_is_stalled_when_heartbeat_is_recent(self) -> None:
        wd = self.make_watchdog(idle_timeout_sec=10)
        heartbeat = {"updated_at": self.iso_ago(2), "agent": "paper-scout", "state": "DISCOVERY"}

        self.assertFalse(wd.is_stalled(heartbeat, {"status": "running"}))

    def test_is_pipeline_terminal_for_completed_failed_and_running(self) -> None:
        wd = self.make_watchdog()

        self.assertTrue(wd.is_pipeline_terminal({"status": "completed"}))
        self.assertTrue(wd.is_pipeline_terminal({"status": "failed"}))
        self.assertFalse(wd.is_pipeline_terminal({"status": "running"}))

    def test_write_resume_request_writes_expected_format(self) -> None:
        wd = self.make_watchdog(idle_timeout_sec=10, max_resume=3)
        wd.state.stall_count = 2
        run_state = {"current_state": "ANALYSIS"}
        heartbeat = {
            "updated_at": self.iso_ago(30),
            "agent": "paper-analyzer",
            "state": "ANALYSIS",
        }

        wd.write_resume_request(run_state, heartbeat)

        request = json.loads(wd.resume_request_path.read_text(encoding="utf-8"))
        self.assertEqual(request["current_state"], "ANALYSIS")
        self.assertEqual(request["suggested_action"], "resume_analysis")
        self.assertEqual(request["stall_count"], 2)
        self.assertEqual(request["resume_count"], 1)
        self.assertIn("No heartbeat for", request["reason"])
        self.assertEqual(wd.state.resume_count, 1)
        self.assertTrue(wd.watchdog_state_path.exists())

    def test_write_resume_request_honors_max_resume_limit(self) -> None:
        wd = self.make_watchdog(max_resume=2)
        wd.state.resume_count = 2

        wd.write_resume_request({"current_state": "VERIFY"}, None)

        self.assertFalse(wd.resume_request_path.exists())

    def test_run_exits_immediately_when_pipeline_is_terminal(self) -> None:
        wd = self.make_watchdog(poll_sec=1)
        self.write_json(
            wd.run_state_path,
            {"status": "completed", "current_state": "DONE"},
        )

        with mock.patch("engine.watchdog.time.sleep", side_effect=AssertionError("sleep should not be called")):
            result = wd.run()

        self.assertEqual(result["exit_reason"], "pipeline_completed")
        self.assertEqual(result["stall_count"], 0)
        self.assertEqual(result["resume_count"], 0)


if __name__ == "__main__":
    unittest.main()
