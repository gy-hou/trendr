import csv
import json
import tempfile
import unittest
from pathlib import Path

from engine.research_history import build_record, history_paths, update_research_history


class ResearchHistoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo_root = self.root / "repo"
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.project_dir = self.root / "project"
        (self.project_dir / "notes").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_candidates(self, count: int) -> None:
        path = self.project_dir / "candidates.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["paper_id", "title"])
            for index in range(count):
                writer.writerow([f"p{index}", f"Paper {index}"])

    def write_notes(self, count: int) -> None:
        for index in range(count):
            (self.project_dir / "notes" / f"p{index}.md").write_text("---\n---\n", encoding="utf-8")

    def make_state(self, **overrides) -> dict:
        state = {
            "run_id": "run-1",
            "project": "project",
            "status": "completed",
            "platform": "cli",
            "started_at": "2026-04-17T01:00:00Z",
            "finished_at": "2026-04-17T01:12:00Z",
            "duration_sec": 720,
            "discovery_rounds": 2,
            "fix_rounds": 0,
            "params": {
                "topic": "多智能体辩论",
                "profile": "basic",
            },
        }
        state.update(overrides)
        if "params" in overrides and isinstance(overrides["params"], dict):
            merged = {
                "topic": "多智能体辩论",
                "profile": "basic",
            }
            merged.update(overrides["params"])
            state["params"] = merged
        return state

    def test_build_record_counts_papers_and_notes(self) -> None:
        self.write_candidates(3)
        self.write_notes(2)

        record = build_record(self.project_dir, self.make_state())

        self.assertEqual(record["topic"], "多智能体辩论")
        self.assertEqual(record["paper_count"], 3)
        self.assertEqual(record["notes_count"], 2)
        self.assertEqual(record["duration_sec"], 720)

    def test_update_research_history_writes_markdown_and_json(self) -> None:
        self.write_candidates(4)
        self.write_notes(1)

        result = update_research_history(
            repo_root=self.repo_root,
            project_dir=self.project_dir,
            state=self.make_state(),
            interactive=False,
        )

        json_path, markdown_path = history_paths(self.repo_root)
        self.assertEqual(result["action"], "added")
        self.assertTrue(json_path.exists())
        self.assertTrue(markdown_path.exists())

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertEqual(len(payload["records"]), 1)
        self.assertIn("多智能体辩论", markdown)
        self.assertIn("Overall Search Time", markdown)
        self.assertIn("Today's Search Time", markdown)

    def test_update_research_history_updates_existing_run_on_resume(self) -> None:
        self.write_candidates(1)
        first = update_research_history(
            repo_root=self.repo_root,
            project_dir=self.project_dir,
            state=self.make_state(status="failed", duration_sec=60),
            interactive=False,
        )
        self.assertEqual(first["action"], "added")

        self.write_candidates(5)
        self.write_notes(3)
        second = update_research_history(
            repo_root=self.repo_root,
            project_dir=self.project_dir,
            state=self.make_state(status="completed", duration_sec=600),
            interactive=False,
        )

        payload = json.loads(history_paths(self.repo_root)[0].read_text(encoding="utf-8"))
        self.assertEqual(second["action"], "updated")
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["status"], "completed")
        self.assertEqual(payload["records"][0]["paper_count"], 5)
        self.assertEqual(payload["records"][0]["notes_count"], 3)

    def test_update_research_history_overflow_fifo(self) -> None:
        for index in range(2):
            project_dir = self.root / f"project-{index}"
            (project_dir / "notes").mkdir(parents=True, exist_ok=True)
            update_research_history(
                repo_root=self.repo_root,
                project_dir=project_dir,
                state=self.make_state(
                    run_id=f"run-{index}",
                    project=f"project-{index}",
                    params={"topic": f"topic-{index}"},
                ),
                limit=2,
                interactive=False,
            )

        project_dir = self.root / "project-2"
        (project_dir / "notes").mkdir(parents=True, exist_ok=True)
        result = update_research_history(
            repo_root=self.repo_root,
            project_dir=project_dir,
            state=self.make_state(
                run_id="run-2",
                project="project-2",
                params={"topic": "topic-2"},
            ),
            limit=2,
            interactive=False,
        )

        payload = json.loads(history_paths(self.repo_root)[0].read_text(encoding="utf-8"))
        topics = [row["topic"] for row in payload["records"]]
        self.assertEqual(result["overflow_action"], "fifo")
        self.assertEqual(len(payload["records"]), 2)
        self.assertEqual(topics, ["topic-1", "topic-2"])

    def test_update_research_history_overflow_prompt_append(self) -> None:
        for index in range(2):
            project_dir = self.root / f"append-project-{index}"
            (project_dir / "notes").mkdir(parents=True, exist_ok=True)
            update_research_history(
                repo_root=self.repo_root,
                project_dir=project_dir,
                state=self.make_state(
                    run_id=f"append-run-{index}",
                    project=f"append-project-{index}",
                    params={"topic": f"append-topic-{index}"},
                ),
                limit=2,
                interactive=False,
                overflow_policy="append",
            )

        project_dir = self.root / "append-project-2"
        (project_dir / "notes").mkdir(parents=True, exist_ok=True)
        result = update_research_history(
            repo_root=self.repo_root,
            project_dir=project_dir,
            state=self.make_state(
                run_id="append-run-2",
                project="append-project-2",
                params={"topic": "append-topic-2"},
            ),
            limit=2,
            interactive=True,
            overflow_policy="prompt",
            prompt_fn=lambda _: "a",
        )

        payload = json.loads(history_paths(self.repo_root)[0].read_text(encoding="utf-8"))
        self.assertEqual(result["overflow_action"], "append")
        self.assertEqual(len(payload["records"]), 3)


if __name__ == "__main__":
    unittest.main()
