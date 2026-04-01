import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cli as trendr_cli
from engine.adapters.cli import CLIAdapter


class CLIAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        soul_dir = self.root / "agents" / "paper-scout"
        soul_dir.mkdir(parents=True, exist_ok=True)
        (soul_dir / "SOUL.md").write_text(
            "# Paper Scout Soul\n\nYou search papers carefully.\n",
            encoding="utf-8",
        )
        self.adapter = CLIAdapter(repo_root=self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_spawn_agent_calls_anthropic_api_and_await_returns_result(self) -> None:
        response = mock.MagicMock()
        response.read.return_value = json.dumps(
            {
                "id": "msg_123",
                "model": "claude-sonnet-4-20250514",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "content": [{"type": "text", "text": "search completed"}],
            }
        ).encode("utf-8")
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=response) as mocked_urlopen:
                handle = self.adapter.spawn_agent("paper-scout", "Find recent RL papers", timeout_sec=42)

        result = self.adapter.await_agent(handle)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["output"], "search completed")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.headers["X-api-key"], "test-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "claude-sonnet-4-20250514")
        self.assertEqual(payload["system"], "# Paper Scout Soul\n\nYou search papers carefully.\n")
        self.assertIn("Find recent RL papers", payload["messages"][0]["content"])

    def test_spawn_agent_uses_trendr_model_override(self) -> None:
        response = mock.MagicMock()
        response.read.return_value = json.dumps(
            {"content": [{"type": "text", "text": "ok"}]}
        ).encode("utf-8")
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with mock.patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "TRENDR_MODEL": "claude-custom-model"},
            clear=False,
        ):
            with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=response) as mocked_urlopen:
                self.adapter.spawn_agent("paper-scout", "Task")

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "claude-custom-model")

    def test_spawn_agent_without_api_key_raises_runtime_error(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                self.adapter.spawn_agent("paper-scout", "Find papers")

        self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))

    def test_http_get_uses_urlopen(self) -> None:
        response = mock.MagicMock()
        response.read.return_value = b'{"ok": true}'
        response.getcode.return_value = 200
        response.headers.items.return_value = [("Content-Type", "application/json")]
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=response):
            result = self.adapter.http_get("https://example.com/data", headers={"Accept": "application/json"})

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["body"], '{"ok": true}')
        self.assertEqual(result["headers"]["Content-Type"], "application/json")

    def test_write_and_read_file(self) -> None:
        path = self.root / "artifacts" / "note.txt"
        self.adapter.write_file(path, "hello")

        self.assertEqual(self.adapter.read_file(path), "hello")

    def test_send_heartbeat_writes_file_and_prints(self) -> None:
        project_dir = self.root / "project"
        project_dir.mkdir()
        state = {
            "agent": "paper-scout",
            "state": "DISCOVERY",
            "updated_at": "2026-04-01T00:00:00Z",
            "message": "working",
        }

        with mock.patch("builtins.print") as mocked_print:
            self.adapter.send_heartbeat(project_dir, state)

        heartbeat = json.loads((project_dir / "heartbeat.json").read_text(encoding="utf-8"))
        self.assertEqual(heartbeat["state"], "DISCOVERY")
        mocked_print.assert_called_once()

    def test_browser_eval_returns_fallback_when_node_unavailable(self) -> None:
        with mock.patch("engine.adapters.cli.subprocess.run", side_effect=FileNotFoundError):
            result = self.adapter.browser_eval("console.log('x')")

        self.assertEqual(result, "browser not available")

    def test_get_adapter_returns_cli_adapter(self) -> None:
        adapter = trendr_cli.get_adapter("cli")

        self.assertIsInstance(adapter, CLIAdapter)

    def test_resolve_run_params_uses_depth_preset_defaults(self) -> None:
        params = trendr_cli.resolve_run_params("A")

        self.assertEqual(
            params,
            {"min_papers": 20, "target_papers": 30, "min_rounds": 2, "max_rounds": 3},
        )

    def test_resolve_run_params_applies_and_normalizes_overrides(self) -> None:
        params = trendr_cli.resolve_run_params(
            "B",
            min_papers=25,
            target_papers=10,
            min_rounds=9,
            max_rounds=4,
        )

        self.assertEqual(
            params,
            {"min_papers": 25, "target_papers": 25, "min_rounds": 4, "max_rounds": 4},
        )


if __name__ == "__main__":
    unittest.main()
