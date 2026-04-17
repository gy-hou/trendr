import json
import unittest
from unittest import mock

from engine.adapters.openclaw import OpenClawAdapter


class OpenClawAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = OpenClawAdapter(mode="cli", browser_profile="cdp")

    def test_run_shell_uses_argv_without_shell(self) -> None:
        proc = mock.MagicMock()
        proc.returncode = 0
        proc.stdout = "ok\n"
        proc.stderr = ""

        with mock.patch("engine.adapters.openclaw.subprocess.run", return_value=proc) as mocked_run:
            result = self.adapter.run_shell("echo hello", timeout_sec=5)

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "ok\n")
        called_args = mocked_run.call_args.args[0]
        self.assertEqual(called_args, ["echo", "hello"])
        self.assertNotIn("shell", mocked_run.call_args.kwargs)

    def test_run_shell_rejects_unsafe_metacharacters(self) -> None:
        with mock.patch("engine.adapters.openclaw.subprocess.run") as mocked_run:
            result = self.adapter.run_shell("echo hello && whoami", timeout_sec=5)

        self.assertEqual(result["exit_code"], 2)
        self.assertIn("unsafe shell metacharacters", result["stderr"])
        mocked_run.assert_not_called()

    def test_browser_eval_cli_uses_non_shell_calls(self) -> None:
        nav_proc = mock.MagicMock()
        nav_proc.returncode = 0
        nav_proc.stdout = "navigated\n"
        nav_proc.stderr = ""

        eval_proc = mock.MagicMock()
        eval_proc.returncode = 0
        eval_proc.stdout = "result\n"
        eval_proc.stderr = ""

        with mock.patch(
            "engine.adapters.openclaw.subprocess.run",
            side_effect=[nav_proc, eval_proc],
        ) as mocked_run:
            output = self.adapter.browser_eval("document.title", "https://example.com")

        self.assertEqual(output, "navigated\nresult")
        first_call = mocked_run.call_args_list[0].args[0]
        second_call = mocked_run.call_args_list[1].args[0]
        self.assertEqual(
            first_call,
            ["openclaw", "browser", "--browser-profile", "cdp", "navigate", "https://example.com"],
        )
        self.assertEqual(
            second_call,
            ["openclaw", "browser", "--browser-profile", "cdp", "eval", "document.title"],
        )
        for call in mocked_run.call_args_list:
            self.assertNotIn("shell", call.kwargs)

    def test_spawn_agent_marks_auth_payload_errors_as_failed(self) -> None:
        proc = mock.MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = json.dumps(
            {
                "status": "ok",
                "summary": "completed",
                "result": {
                    "payloads": [
                        {"text": "HTTP 401 authentication_error: invalid api key"}
                    ],
                    "stopReason": "error",
                    "completion": {
                        "stopReason": "error",
                        "finishReason": "error",
                    },
                },
            }
        )

        with mock.patch("engine.adapters.openclaw.subprocess.run", return_value=proc):
            handle = self.adapter.spawn_agent("paper-scout", "health check", timeout_sec=5)

        result = self.adapter.await_agent(handle)
        self.assertEqual(result["status"], "failed")
        self.assertIn("invalid api key", result["output"])
        self.assertIn("invalid api key", result["error"])

    def test_spawn_agent_marks_stop_reason_errors_as_failed(self) -> None:
        proc = mock.MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = json.dumps(
            {
                "status": "ok",
                "summary": "completed",
                "result": {
                    "payloads": [{"text": "agent stopped unexpectedly"}],
                    "stopReason": "error",
                },
            }
        )

        with mock.patch("engine.adapters.openclaw.subprocess.run", return_value=proc):
            handle = self.adapter.spawn_agent("paper-scout", "health check", timeout_sec=5)

        result = self.adapter.await_agent(handle)
        self.assertEqual(result["status"], "failed")
        self.assertIn("agent stopped unexpectedly", result["output"])

    def test_spawn_agent_keeps_clean_json_results_completed(self) -> None:
        proc = mock.MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = json.dumps(
            {
                "status": "ok",
                "summary": "completed",
                "result": {
                    "payloads": [{"text": "wrote candidates.csv"}],
                    "stopReason": "completed",
                    "completion": {
                        "stopReason": "completed",
                        "finishReason": "stop",
                    },
                },
            }
        )

        with mock.patch("engine.adapters.openclaw.subprocess.run", return_value=proc):
            handle = self.adapter.spawn_agent("paper-scout", "health check", timeout_sec=5)

        result = self.adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["output"], "wrote candidates.csv")
        self.assertEqual(result["error"], "")


if __name__ == "__main__":
    unittest.main()
