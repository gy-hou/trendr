import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

import cli as trendr_cli
from engine.adapters.cli import CLIAdapter
from engine.runtime import detect_runtime, normalize_runtime


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

        with mock.patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "TRENDR_PROVIDER": "anthropic"},
            clear=False,
        ):
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
            {
                "ANTHROPIC_API_KEY": "test-key",
                "TRENDR_PROVIDER": "anthropic",
                "TRENDR_MODEL": "claude-custom-model",
            },
            clear=False,
        ):
            with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=response) as mocked_urlopen:
                self.adapter.spawn_agent("paper-scout", "Task")

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "claude-custom-model")

    def test_spawn_agent_auto_prefers_openai_when_both_keys_exist(self) -> None:
        response = mock.MagicMock()
        response.read.return_value = json.dumps(
            {
                "id": "chatcmpl_123",
                "model": "gpt-5.4-mini",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "openai path"},
                    }
                ],
                "usage": {"prompt_tokens": 8, "completion_tokens": 3},
            }
        ).encode("utf-8")
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with mock.patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "openai-key", "ANTHROPIC_API_KEY": "anthropic-key"},
            clear=False,
        ):
            with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=response) as mocked_urlopen:
                handle = self.adapter.spawn_agent("paper-scout", "Find papers")

        result = self.adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["output"], "openai path")
        request = mocked_urlopen.call_args.args[0]
        self.assertIn("/chat/completions", request.full_url)
        self.assertEqual(request.headers["Authorization"], "Bearer openai-key")

    def test_spawn_agent_respects_anthropic_provider_override(self) -> None:
        response = mock.MagicMock()
        response.read.return_value = json.dumps(
            {
                "id": "msg_456",
                "model": "claude-sonnet-4-20250514",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 7, "output_tokens": 4},
                "content": [{"type": "text", "text": "anthropic forced"}],
            }
        ).encode("utf-8")
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with mock.patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "openai-key",
                "ANTHROPIC_API_KEY": "anthropic-key",
                "TRENDR_PROVIDER": "anthropic",
            },
            clear=False,
        ):
            with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=response) as mocked_urlopen:
                handle = self.adapter.spawn_agent("paper-scout", "Find papers")

        result = self.adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "anthropic")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")

    def test_spawn_agent_without_api_key_raises_runtime_error(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                self.adapter.spawn_agent("paper-scout", "Find papers")

        self.assertIn("OPENAI_API_KEY", str(ctx.exception))

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
        self.assertEqual(adapter.platform_name, "cli")

    def test_get_adapter_returns_codex_runtime_adapter(self) -> None:
        adapter = trendr_cli.get_adapter("codex")
        self.assertIsInstance(adapter, CLIAdapter)
        self.assertEqual(adapter.platform_name, "codex")

    def test_get_adapter_normalizes_claudecode_alias(self) -> None:
        adapter = trendr_cli.get_adapter("claudecode")
        self.assertIsInstance(adapter, CLIAdapter)
        self.assertEqual(adapter.platform_name, "claude-code")

    def test_runtime_normalization(self) -> None:
        self.assertEqual(normalize_runtime("claudecode"), "claude-code")
        self.assertEqual(normalize_runtime("codex"), "codex")
        self.assertEqual(normalize_runtime("unknown-platform"), "cli")

    def test_detect_runtime_priority(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "TRENDR_PLATFORM": "claudecode",
                "OPENCLAW_SESSION_ID": "oc-123",
                "CODEX_SHELL": "1",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            clear=True,
        ):
            self.assertEqual(detect_runtime(os.environ), "claude-code")

        with mock.patch.dict(
            os.environ,
            {"OPENCLAW_SESSION_ID": "oc-123", "CODEX_SHELL": "1"},
            clear=True,
        ):
            self.assertEqual(detect_runtime(os.environ), "openclaw")

        with mock.patch.dict(
            os.environ,
            {"CODEX_SHELL": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
            clear=True,
        ):
            self.assertEqual(detect_runtime(os.environ), "codex")

        with mock.patch.dict(
            os.environ,
            {"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
            clear=True,
        ):
            self.assertEqual(detect_runtime(os.environ), "claude-code")

    def test_cli_detect_platform_uses_runtime_detection(self) -> None:
        with mock.patch.dict(os.environ, {"CODEX_SHELL": "1"}, clear=True):
            self.assertEqual(trendr_cli.detect_platform(), "codex")

    def test_normalize_user_command_tokens_supports_multilingual_shortcuts(self) -> None:
        self.assertEqual(trendr_cli.normalize_user_command_tokens(["/tr", "热点"]), ["hotspots"])
        self.assertEqual(trendr_cli.normalize_user_command_tokens(["/tr", "hot"]), ["hotspots"])
        self.assertEqual(trendr_cli.normalize_user_command_tokens(["/tr", "研究"]), ["run"])
        self.assertEqual(trendr_cli.normalize_user_command_tokens(["/tr", "research"]), ["run"])
        self.assertEqual(trendr_cli.normalize_user_command_tokens(["/", "tr", "research"]), ["run"])

    def test_main_routes_slash_tr_hot_to_hotspots_command(self) -> None:
        with mock.patch("cli.cmd_hotspots", return_value=0) as mocked_hotspots:
            with self.assertRaises(SystemExit) as ctx:
                trendr_cli.main(["/tr", "hot"])

        self.assertEqual(ctx.exception.code, 0)
        mocked_hotspots.assert_called_once()

    def test_main_routes_slash_tr_research_to_run_command(self) -> None:
        with mock.patch("cli.cmd_run", return_value=0) as mocked_run:
            with self.assertRaises(SystemExit) as ctx:
                trendr_cli.main(["/tr", "research", "--topic", "demo topic"])

        self.assertEqual(ctx.exception.code, 0)
        mocked_run.assert_called_once()

    def test_cmd_run_with_codex_platform_persists_platform(self) -> None:
        project_dir = self.root / "codex-run"
        args = Namespace(
            platform="codex",
            topic="Codex platform smoke test",
            depth="A",
            profile="basic",
            project_dir=str(project_dir),
            time_budget=10,
            min_papers=None,
            target_papers=None,
            min_rounds=None,
            max_rounds=None,
            hotspots_limit=10,
            hotspots_timeout=12,
            no_watchdog=True,
        )

        with mock.patch("engine.state_machine.ResearchStateMachine.run", return_value={"status": "completed", "duration_sec": 1, "run_id": "r1"}):
            code = trendr_cli.cmd_run(args)

        self.assertEqual(code, 0)
        state = json.loads((project_dir / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["platform"], "codex")
        self.assertEqual(state["params"]["profile"], "basic")

    def test_cmd_run_rejects_lite_profile_and_points_to_hotspots(self) -> None:
        args = Namespace(
            platform="cli",
            topic="Lite route",
            depth="A",
            profile="lite",
            project_dir=str(self.root / "lite-route"),
            time_budget=10,
            min_papers=None,
            target_papers=None,
            min_rounds=None,
            max_rounds=None,
            hotspots_limit=10,
            hotspots_timeout=12,
            no_watchdog=True,
        )

        with mock.patch("builtins.print") as mocked_print:
            code = trendr_cli.cmd_run(args)

        self.assertEqual(code, 2)
        self.assertTrue(mocked_print.called)
        printed = mocked_print.call_args.args[0]
        self.assertIn("trendr hotspots", printed)

    def test_cmd_hotspots_runs_independent_lite_flow(self) -> None:
        project_dir = self.root / "hotspots-only"
        args = Namespace(
            topic="AI infra",
            project_dir=str(project_dir),
            per_source_limit=7,
            timeout_sec=9,
        )

        with mock.patch("engine.hotspots_runner.HotspotsRunner") as mocked_runner:
            mocked_runner.return_value.run.return_value = {
                "status": "completed",
                "project_dir": str(project_dir.resolve()),
                "raw_path": str(project_dir.resolve() / "hotspots_raw.json"),
                "summary_path": str(project_dir.resolve() / "hotspots_summary.json"),
                "report_path": str(project_dir.resolve() / "hotspots_report.md"),
                "item_count": 12,
                "sources_ok": 3,
                "sources_total": 4,
            }
            code = trendr_cli.cmd_hotspots(args)

        self.assertEqual(code, 0)
        mocked_runner.assert_called_once()
        called = mocked_runner.call_args.kwargs
        self.assertEqual(called["project_dir"], project_dir.resolve())
        self.assertEqual(called["topic"], "AI infra")
        self.assertEqual(called["per_source_limit"], 7)
        self.assertEqual(called["timeout_sec"], 9)

    def test_cmd_hotspots_template_writes_template_and_private_files(self) -> None:
        cfg_dir = self.root / "hotspots-config"
        template = cfg_dir / "template.json"
        private = cfg_dir / "private.json"
        args = Namespace(
            template_path=str(template),
            private_path=str(private),
            force=False,
        )

        code = trendr_cli.cmd_hotspots_template(args)

        self.assertEqual(code, 0)
        self.assertTrue(template.exists())
        self.assertTrue(private.exists())

        template_payload = json.loads(template.read_text(encoding="utf-8"))
        private_payload = json.loads(private.read_text(encoding="utf-8"))
        self.assertEqual(template_payload.get("profile"), "lite")
        self.assertIn("keywords", private_payload)
        self.assertIn("upload", private_payload)

    def test_cmd_run_full_profile_triggers_hotspots_post_run(self) -> None:
        project_dir = self.root / "full-run"
        args = Namespace(
            platform="cli",
            topic="Full profile smoke",
            depth="B",
            profile="full",
            project_dir=str(project_dir),
            time_budget=10,
            min_papers=None,
            target_papers=None,
            min_rounds=None,
            max_rounds=None,
            hotspots_limit=6,
            hotspots_timeout=8,
            no_watchdog=True,
        )

        with mock.patch(
            "engine.state_machine.ResearchStateMachine.run",
            return_value={"status": "completed", "duration_sec": 1, "run_id": "r2"},
        ):
            with mock.patch("engine.hotspots_runner.HotspotsRunner") as mocked_runner:
                mocked_runner.return_value.run.return_value = {
                    "status": "completed",
                    "item_count": 20,
                    "sources_ok": 4,
                    "sources_total": 4,
                }
                code = trendr_cli.cmd_run(args)

        self.assertEqual(code, 0)
        mocked_runner.assert_called_once()
        called = mocked_runner.call_args.kwargs
        self.assertEqual(called["project_dir"], project_dir.resolve())
        self.assertEqual(called["topic"], "Full profile smoke")
        self.assertEqual(called["per_source_limit"], 6)
        self.assertEqual(called["timeout_sec"], 8)

    def test_cmd_resume_accepts_claudecode_alias(self) -> None:
        project_dir = self.root / "resume-claude"
        project_dir.mkdir(parents=True, exist_ok=True)

        adapter = CLIAdapter(repo_root=self.root, platform_name="cli")
        from engine.state_machine import ResearchStateMachine

        sm = ResearchStateMachine(project_dir, adapter)
        sm.initialize(topic="Resume test", run_id="resume-1", min_papers=1)

        args = Namespace(platform="claudecode", project_dir=str(project_dir))

        with mock.patch("engine.state_machine.ResearchStateMachine.run", return_value={"status": "completed"}):
            code = trendr_cli.cmd_resume(args)

        self.assertEqual(code, 0)

    def test_codex_runtime_uses_native_session_without_login_precheck(self) -> None:
        adapter = CLIAdapter(repo_root=self.root, platform_name="codex")

        codex_run = mock.MagicMock()
        codex_run.returncode = 0
        codex_run.stdout = "native codex ok\n"
        codex_run.stderr = ""

        with mock.patch("engine.adapters.cli.shutil.which", return_value="/usr/local/bin/codex"):
            with mock.patch("engine.adapters.cli.subprocess.run", return_value=codex_run) as mocked_run:
                with mock.patch.dict(os.environ, {}, clear=True):
                    handle = adapter.spawn_agent("paper-scout", "Find papers")

        result = adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "codex-cli")
        self.assertEqual(result["output"], "native codex ok")
        self.assertEqual(mocked_run.call_count, 1)
        called_cmd = mocked_run.call_args.args[0]
        self.assertGreaterEqual(len(called_cmd), 2)
        self.assertEqual(called_cmd[0], "codex")
        self.assertEqual(called_cmd[1], "exec")

    def test_codex_runtime_in_codex_app_env_works_without_api_keys(self) -> None:
        adapter = CLIAdapter(repo_root=self.root, platform_name="codex")

        codex_run = mock.MagicMock()
        codex_run.returncode = 0
        codex_run.stdout = "codex app session ok\n"
        codex_run.stderr = ""

        with mock.patch("engine.adapters.cli.shutil.which", return_value="/usr/local/bin/codex"):
            with mock.patch("engine.adapters.cli.subprocess.run", return_value=codex_run):
                with mock.patch.dict(
                    os.environ,
                    {
                        "CODEX_SHELL": "1",
                        "CODEX_THREAD_ID": "thread-1",
                    },
                    clear=True,
                ):
                    handle = adapter.spawn_agent("paper-scout", "Find papers")

        result = adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "codex-cli")
        self.assertEqual(result["output"], "codex app session ok")

    def test_codex_runtime_reports_actionable_error_without_api_key_fallback(self) -> None:
        adapter = CLIAdapter(repo_root=self.root, platform_name="codex")

        codex_run = mock.MagicMock()
        codex_run.returncode = 1
        codex_run.stdout = ""
        codex_run.stderr = "Not logged in"

        with mock.patch("engine.adapters.cli.shutil.which", return_value="/usr/local/bin/codex"):
            with mock.patch("engine.adapters.cli.subprocess.run", return_value=codex_run):
                with mock.patch.dict(os.environ, {}, clear=True):
                    with self.assertRaises(RuntimeError) as ctx:
                        adapter.spawn_agent("paper-scout", "Find papers")

        msg = str(ctx.exception)
        self.assertIn("codex exec failed", msg)
        self.assertIn("codex login", msg)
        self.assertIn("OPENAI_API_KEY", msg)

    def test_codex_runtime_error_message_is_summarized(self) -> None:
        adapter = CLIAdapter(repo_root=self.root, platform_name="codex")

        codex_run = mock.MagicMock()
        codex_run.returncode = 1
        codex_run.stdout = (
            "OpenAI Codex banner line\n"
            "user\n"
            "very long prompt content\n"
            "ERROR: unexpected status 401 Unauthorized: Missing bearer authentication\n"
        )
        codex_run.stderr = ""

        with mock.patch("engine.adapters.cli.shutil.which", return_value="/usr/local/bin/codex"):
            with mock.patch("engine.adapters.cli.subprocess.run", return_value=codex_run):
                with mock.patch.dict(os.environ, {}, clear=True):
                    with self.assertRaises(RuntimeError) as ctx:
                        adapter.spawn_agent("paper-scout", "Find papers")

        msg = str(ctx.exception)
        self.assertIn("401 Unauthorized", msg)
        self.assertNotIn("very long prompt content", msg)

    def test_codex_runtime_falls_back_to_openai_key_when_native_exec_fails(self) -> None:
        adapter = CLIAdapter(repo_root=self.root, platform_name="codex")

        codex_run = mock.MagicMock()
        codex_run.returncode = 1
        codex_run.stdout = ""
        codex_run.stderr = "Not logged in"

        api_response = mock.MagicMock()
        api_response.read.return_value = json.dumps(
            {
                "id": "chatcmpl_fallback",
                "model": "gpt-5.4-mini",
                "choices": [{"finish_reason": "stop", "message": {"content": "fallback ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            }
        ).encode("utf-8")
        api_response.__enter__.return_value = api_response
        api_response.__exit__.return_value = False

        with mock.patch("engine.adapters.cli.shutil.which", return_value="/usr/local/bin/codex"):
            with mock.patch("engine.adapters.cli.subprocess.run", return_value=codex_run):
                with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}, clear=False):
                    with mock.patch("engine.adapters.cli.urllib.request.urlopen", return_value=api_response):
                        handle = adapter.spawn_agent("paper-scout", "Find papers")

        result = adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["output"], "fallback ok")

    def test_claude_code_runtime_uses_native_logged_in_session_without_api_key(self) -> None:
        adapter = CLIAdapter(repo_root=self.root, platform_name="claude-code")

        auth_status = mock.MagicMock()
        auth_status.returncode = 0
        auth_status.stdout = json.dumps({"loggedIn": True, "authMethod": "claude.ai"})
        auth_status.stderr = ""

        claude_run = mock.MagicMock()
        claude_run.returncode = 0
        claude_run.stdout = "native claude ok\n"
        claude_run.stderr = ""

        with mock.patch("engine.adapters.cli.shutil.which", return_value="/usr/local/bin/claude"):
            with mock.patch("engine.adapters.cli.subprocess.run", side_effect=[auth_status, claude_run]):
                with mock.patch.dict(os.environ, {}, clear=True):
                    handle = adapter.spawn_agent("paper-scout", "Find papers")

        result = adapter.await_agent(handle)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "claude-cli")
        self.assertEqual(result["output"], "native claude ok")

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
