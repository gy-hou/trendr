import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.adapters.base import PlatformAdapter
from engine.state_machine import DEFAULT_MAX_FIX_ROUNDS, ResearchStateMachine
from engine.validators import ArtifactValidator


class DummyAdapter(PlatformAdapter):
    def __init__(self) -> None:
        self.heartbeats = []

    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int = 900) -> str:
        return f"{agent_id}-handle"

    def await_agent(self, handle: str, poll_sec: int = 10) -> dict:
        return {"status": "completed", "output": handle}

    def http_get(self, url: str, headers: dict | None = None) -> dict:
        return {"status_code": 200, "body": "", "headers": headers or {}}

    def read_file(self, path: Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_shell(self, command: str, timeout_sec: int = 30) -> dict:
        return {"exit_code": 0, "stdout": "", "stderr": ""}

    def send_heartbeat(self, project_dir: Path, state: dict) -> None:
        self.heartbeats.append({"project_dir": str(project_dir), **state})

    def browser_eval(self, js: str, url: str | None = None) -> str:
        return ""

    @property
    def platform_name(self) -> str:
        return "dummy"


class ResearchStateMachineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.adapter = DummyAdapter()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_machine(self, name: str = "project") -> ResearchStateMachine:
        project_dir = self.root / name
        return ResearchStateMachine(project_dir=project_dir, adapter=self.adapter)

    def initialize_machine(self, name: str = "project", **kwargs) -> ResearchStateMachine:
        sm = self.make_machine(name)
        params = {
            "topic": "TrendR testing",
            "min_papers": 2,
            "run_id": "run-001",
        }
        params.update(kwargs)
        sm.initialize(**params)
        return sm

    def write(self, path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_candidates(self, sm: ResearchStateMachine, rows: list[dict]) -> Path:
        header = "paper_id,title,authors,year,source,relevance_score,url\n"
        body = "".join(
            f"{row['paper_id']},{row['title']},{row['authors']},{row['year']},"
            f"{row['source']},{row['relevance_score']},{row['url']}\n"
            for row in rows
        )
        return self.write(sm.candidates_path, header + body)

    def write_matrix(self, sm: ResearchStateMachine, rows: list[dict]) -> Path:
        header = "paper_id,method,dataset,category\n"
        body = "".join(
            f"{row['paper_id']},{row['method']},{row['dataset']},{row['category']}\n"
            for row in rows
        )
        return self.write(sm.matrix_path, header + body)

    def write_note(self, sm: ResearchStateMachine, filename: str, content: str) -> Path:
        return self.write(sm.notes_dir / filename, content)

    def write_review_and_bib(self, sm: ResearchStateMachine) -> None:
        review_body = ("TrendR review content. " * 40).strip()
        self.write(
            sm.review_path,
            f"# Review\n\n{review_body}\n\n\\cite{{paper1}}\n\n## References\n\n- Example\n",
        )
        self.write(
            sm.references_path,
            textwrap.dedent(
                """
                @article{paper1,
                  title={Paper One},
                  author={Alice},
                  year={2024}
                }
                """
            ).strip(),
        )

    def test_initialize_creates_expected_structure_and_schema(self) -> None:
        sm = self.make_machine("init-project")
        state = sm.initialize(
            topic="Agentic literature reviews",
            depth="C",
            min_papers=12,
            target_papers=24,
            min_rounds=2,
            max_rounds=5,
            time_budget_min=90,
            run_id="init-123",
        )

        self.assertTrue((sm.project_dir / "notes").is_dir())
        self.assertTrue((sm.project_dir / "logs").is_dir())
        self.assertTrue((sm.project_dir / "papers").is_dir())
        self.assertTrue(sm.progress_path.exists())
        self.assertTrue((sm.project_dir / "logs" / "init-123.log").exists())
        self.assertTrue((sm.project_dir / "logs" / "latest.log").exists())
        self.assertTrue(ArtifactValidator.validate_run_state(sm.state_path).ok)

        saved = json.loads(sm.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["run_id"], "init-123")
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["current_state"], "INIT")
        self.assertEqual(saved["status"], "running")
        self.assertEqual(saved["params"]["topic"], "Agentic literature reviews")
        self.assertEqual(saved["params"]["min_papers"], 12)
        self.assertEqual(saved["params"]["target_papers"], 24)
        self.assertEqual(saved["params"]["min_rounds"], 2)
        self.assertEqual(saved["params"]["max_rounds"], 5)
        self.assertEqual(saved["history"][0]["state"], "INIT")

    def test_check_transition_from_init_to_discovery(self) -> None:
        sm = self.initialize_machine("init-transition")

        self.assertEqual(sm.check_transition(), "DISCOVERY")

    def test_check_transition_from_discovery_to_analysis(self) -> None:
        sm = self.initialize_machine("discovery-transition")
        sm.state["current_state"] = "DISCOVERY"
        sm.state["discovery_rounds"] = 1
        self.write_candidates(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "title": "Paper One",
                    "authors": "Alice",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "5",
                    "url": "https://example.com/p1",
                },
                {
                    "paper_id": "paper2",
                    "title": "Paper Two",
                    "authors": "Bob",
                    "year": "2023",
                    "source": "openalex",
                    "relevance_score": "4",
                    "url": "https://example.com/p2",
                },
            ],
        )

        self.assertEqual(sm.check_transition(), "ANALYSIS")

    def test_check_transition_from_discovery_retries_when_below_minimum(self) -> None:
        sm = self.initialize_machine("discovery-retry", min_papers=3, max_rounds=3)
        sm.state["current_state"] = "DISCOVERY"
        sm.state["discovery_rounds"] = 1
        self.write_candidates(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "title": "Paper One",
                    "authors": "Alice",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "5",
                    "url": "https://example.com/p1",
                }
            ],
        )

        self.assertEqual(sm.check_transition(), "DISCOVERY")

    def test_check_transition_from_discovery_honors_min_rounds_even_when_minimum_is_met(self) -> None:
        sm = self.initialize_machine(
            "discovery-min-rounds",
            min_papers=2,
            target_papers=2,
            min_rounds=2,
            max_rounds=3,
        )
        sm.state["current_state"] = "DISCOVERY"
        sm.state["discovery_rounds"] = 1
        self.write_candidates(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "title": "Paper One",
                    "authors": "Alice",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "5",
                    "url": "https://example.com/p1",
                },
                {
                    "paper_id": "paper2",
                    "title": "Paper Two",
                    "authors": "Bob",
                    "year": "2023",
                    "source": "openalex",
                    "relevance_score": "4",
                    "url": "https://example.com/p2",
                },
            ],
        )

        self.assertEqual(sm.check_transition(), "DISCOVERY")

    def test_check_transition_from_discovery_retries_until_target_is_met(self) -> None:
        sm = self.initialize_machine(
            "discovery-target",
            min_papers=2,
            target_papers=4,
            min_rounds=1,
            max_rounds=3,
        )
        sm.state["current_state"] = "DISCOVERY"
        sm.state["discovery_rounds"] = 1
        self.write_candidates(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "title": "Paper One",
                    "authors": "Alice",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "5",
                    "url": "https://example.com/p1",
                },
                {
                    "paper_id": "paper2",
                    "title": "Paper Two",
                    "authors": "Bob",
                    "year": "2023",
                    "source": "openalex",
                    "relevance_score": "4",
                    "url": "https://example.com/p2",
                },
            ],
        )

        self.assertEqual(sm.check_transition(), "DISCOVERY")

    def test_check_transition_from_discovery_advances_after_target_is_met(self) -> None:
        sm = self.initialize_machine(
            "discovery-target-hit",
            min_papers=2,
            target_papers=4,
            min_rounds=2,
            max_rounds=3,
        )
        sm.state["current_state"] = "DISCOVERY"
        sm.state["discovery_rounds"] = 2
        self.write_candidates(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "title": "Paper One",
                    "authors": "Alice",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "5",
                    "url": "https://example.com/p1",
                },
                {
                    "paper_id": "paper2",
                    "title": "Paper Two",
                    "authors": "Bob",
                    "year": "2023",
                    "source": "openalex",
                    "relevance_score": "4",
                    "url": "https://example.com/p2",
                },
                {
                    "paper_id": "paper3",
                    "title": "Paper Three",
                    "authors": "Cara",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "4",
                    "url": "https://example.com/p3",
                },
                {
                    "paper_id": "paper4",
                    "title": "Paper Four",
                    "authors": "Dan",
                    "year": "2025",
                    "source": "dblp",
                    "relevance_score": "4",
                    "url": "https://example.com/p4",
                },
            ],
        )

        self.assertEqual(sm.check_transition(), "ANALYSIS")

    def test_check_transition_from_analysis_to_gap_check(self) -> None:
        sm = self.initialize_machine("analysis-transition")
        sm.state["current_state"] = "ANALYSIS"
        self.write_candidates(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "title": "Paper One",
                    "authors": "Alice",
                    "year": "2024",
                    "source": "arxiv",
                    "relevance_score": "5",
                    "url": "https://example.com/p1",
                }
            ],
        )
        self.write_matrix(
            sm,
            [
                {
                    "paper_id": "paper1",
                    "method": "survey",
                    "dataset": "demo",
                    "category": "analysis",
                }
            ],
        )
        self.write_note(
            sm,
            "paper1.md",
            textwrap.dedent(
                """
                ---
                paper_id: paper1
                title: Paper One
                relevance_score: 5
                ---

                Structured note content.
                """
            ).strip(),
        )

        self.assertEqual(sm.check_transition(), "GAP_CHECK")

    def test_check_transition_from_gap_check_to_writing(self) -> None:
        sm = self.initialize_machine("gap-transition")
        sm.state["current_state"] = "GAP_CHECK"
        self.write(sm.gap_report_path, "# Gap Report\n\ncoverage_score: 0.80\n")

        self.assertEqual(sm.check_transition(), "WRITING")

    def test_check_transition_from_writing_to_verify(self) -> None:
        sm = self.initialize_machine("writing-transition")
        sm.state["current_state"] = "WRITING"
        self.write_review_and_bib(sm)

        self.assertEqual(sm.check_transition(), "VERIFY")

    def test_check_transition_from_verify_to_done(self) -> None:
        sm = self.initialize_machine("verify-transition")
        sm.state["current_state"] = "VERIFY"
        self.write(sm.verify_path, json.dumps({"pass": True, "issues": []}))

        self.assertEqual(sm.check_transition(), "DONE")

    def test_transition_updates_history_and_current_state(self) -> None:
        sm = self.initialize_machine("transition-history")

        sm.transition("DISCOVERY", result="ok", metrics={"row_count": 2})

        self.assertEqual(sm.state["current_state"], "DISCOVERY")
        self.assertEqual(len(sm.state["history"]), 2)
        first_entry = sm.state["history"][0]
        second_entry = sm.state["history"][1]
        self.assertEqual(first_entry["state"], "INIT")
        self.assertEqual(first_entry["result"], "ok")
        self.assertEqual(first_entry["metrics"]["row_count"], 2)
        self.assertIsNotNone(first_entry["exited_at"])
        self.assertEqual(second_entry["state"], "DISCOVERY")
        self.assertIsNone(second_entry["exited_at"])

        saved = json.loads(sm.state_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["current_state"], "DISCOVERY")

    def test_check_gap_exit_loops_back_to_discovery_below_threshold(self) -> None:
        sm = self.initialize_machine("gap-low", max_rounds=3)
        sm.state["current_state"] = "GAP_CHECK"
        sm.state["discovery_rounds"] = 1
        self.write(sm.gap_report_path, "coverage_score: 0.40\n")

        next_state = sm._check_gap_exit()

        self.assertEqual(next_state, "DISCOVERY")
        self.assertEqual(sm.state["discovery_rounds"], 2)

    def test_check_gap_exit_advances_to_writing_above_threshold(self) -> None:
        sm = self.initialize_machine("gap-high")
        sm.state["current_state"] = "GAP_CHECK"
        sm.state["discovery_rounds"] = 1
        self.write(sm.gap_report_path, "coverage_score: 0.85\n")

        next_state = sm._check_gap_exit()

        self.assertEqual(next_state, "WRITING")
        self.assertEqual(sm.state["discovery_rounds"], 1)

    def test_check_verify_exit_advances_to_done_on_pass(self) -> None:
        sm = self.initialize_machine("verify-pass")
        sm.state["current_state"] = "VERIFY"
        self.write(sm.verify_path, json.dumps({"pass": True, "issues": []}))

        next_state = sm._check_verify_exit()

        self.assertEqual(next_state, "DONE")

    def test_check_verify_exit_returns_to_writing_on_failure(self) -> None:
        sm = self.initialize_machine("verify-fail")
        sm.state["current_state"] = "VERIFY"
        self.write(sm.verify_path, json.dumps({"pass": False, "issues": ["missing citation"]}))

        next_state = sm._check_verify_exit()

        self.assertEqual(next_state, "WRITING")
        self.assertEqual(sm.state["fix_rounds"], 1)

    def test_check_verify_exit_forces_done_after_max_fix_rounds(self) -> None:
        sm = self.initialize_machine("verify-max")
        sm.state["current_state"] = "VERIFY"
        sm.state["fix_rounds"] = DEFAULT_MAX_FIX_ROUNDS
        self.write(sm.verify_path, json.dumps({"pass": False, "issues": ["still failing"]}))

        next_state = sm._check_verify_exit()

        self.assertEqual(next_state, "DONE")
        self.assertEqual(sm.state["fix_rounds"], DEFAULT_MAX_FIX_ROUNDS)

    def test_check_budget_returns_force_advance_target(self) -> None:
        sm = self.initialize_machine("budget-map", time_budget_min=0)
        sm.state["current_state"] = "DISCOVERY"
        self.assertEqual(sm._check_budget(), "ANALYSIS")

        sm.state["current_state"] = "ANALYSIS"
        self.assertEqual(sm._check_budget(), "GAP_CHECK")

        sm.state["current_state"] = "GAP_CHECK"
        self.assertEqual(sm._check_budget(), "WRITING")

        sm.state["current_state"] = "WRITING"
        self.assertIsNone(sm._check_budget())

    def test_log_transition_failure_records_validator_details(self) -> None:
        sm = self.initialize_machine("transition-failure")
        sm.transition("ANALYSIS")
        self.write(
            sm.matrix_path,
            "paper_id,title,year,method_category\npaper1,Paper One,2024,survey\n",
        )
        self.write(
            sm.notes_dir / "paper1.md",
            "# Paper One\n\nNo YAML frontmatter here.\n",
        )

        sm._log_transition_failure()

        history_entry = sm.state["history"][-1]
        self.assertIn("validation_errors", history_entry)
        self.assertGreaterEqual(len(history_entry["validation_errors"]), 2)
        log_text = (sm.project_dir / "logs" / "latest.log").read_text(encoding="utf-8")
        self.assertIn("Validator failed: Missing columns", log_text)
        self.assertIn("Validator failed: Only 0/1 notes have valid frontmatter", log_text)

    def test_run_force_advances_when_budget_is_exceeded(self) -> None:
        sm = self.initialize_machine("budget-run", time_budget_min=0)
        sm.transition("ANALYSIS")
        original_execute_current = sm.execute_current

        def fake_execute_current() -> bool:
            if sm.state["current_state"] == "DONE":
                return original_execute_current()
            return True

        def fake_check_transition() -> str | None:
            if sm.state["current_state"] == "GAP_CHECK":
                return "DONE"
            return None

        sm.execute_current = fake_execute_current  # type: ignore[method-assign]
        sm.check_transition = fake_check_transition  # type: ignore[method-assign]

        result = sm.run()

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["budget_exceeded"])
        self.assertEqual(result["history"][1]["state"], "ANALYSIS")
        self.assertEqual(result["history"][1]["result"], "budget_exceeded")
        self.assertEqual(
            [entry["state"] for entry in result["history"]],
            ["INIT", "ANALYSIS", "GAP_CHECK", "DONE"],
        )

    def test_run_retries_discovery_until_transition_condition_is_met(self) -> None:
        sm = self.initialize_machine("run-discovery-retry")
        discovery_checks = iter(["DISCOVERY", "ANALYSIS"])
        original_execute_current = sm.execute_current

        def fake_execute_current() -> bool:
            current = sm.state["current_state"]
            if current == "DISCOVERY":
                sm.state["discovery_rounds"] = sm.state.get("discovery_rounds", 0) + 1
                sm.save_state()
            elif current == "DONE":
                return original_execute_current()
            return True

        def fake_check_transition() -> str | None:
            current = sm.state["current_state"]
            if current == "INIT":
                return "DISCOVERY"
            if current == "DISCOVERY":
                return next(discovery_checks)
            if current == "ANALYSIS":
                return "DONE"
            return None

        sm.execute_current = fake_execute_current  # type: ignore[method-assign]
        sm.check_transition = fake_check_transition  # type: ignore[method-assign]

        result = sm.run()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["current_state"], "DONE")
        self.assertEqual(result["discovery_rounds"], 2)
        self.assertEqual(
            [entry["state"] for entry in result["history"]],
            ["INIT", "DISCOVERY", "DISCOVERY", "ANALYSIS", "DONE"],
        )


if __name__ == "__main__":
    unittest.main()
