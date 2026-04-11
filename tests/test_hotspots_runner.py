import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine.hotspots_runner import (
    HotspotsRunner,
    write_hotspots_private_stub,
    write_hotspots_template,
)


class HotspotsRunnerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name) / "hotspots-project"
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_writes_artifacts_and_deduplicates_items(self) -> None:
        template_path = self.project_dir / "template.json"
        private_path = self.project_dir / "private.json"
        write_hotspots_template(template_path, force=True)
        write_hotspots_private_stub(private_path, force=True)

        runner = HotspotsRunner(
            project_dir=self.project_dir,
            topic="Agents",
            per_source_limit=3,
            timeout_sec=5,
            template_path=template_path,
            private_path=private_path,
            session_path=self.project_dir / "session.json",
        )

        hn_items = [
            {"source": "hackernews", "title": "A", "url": "https://example.com/a", "score": 10, "meta": {}},
            {"source": "hackernews", "title": "B", "url": "https://example.com/b", "score": 8, "meta": {}},
        ]
        gh_items = [
            {"source": "github_trending", "title": "repo/a", "url": "https://github.com/repo/a", "score": 0, "meta": {}},
            {"source": "github_trending", "title": "A dup", "url": "https://example.com/a", "score": 0, "meta": {}},
        ]
        reddit_items = [
            {"source": "reddit", "title": "R1", "url": "https://reddit.com/r/x1", "score": 4, "meta": {}},
        ]
        ph_items = [
            {"source": "producthunt", "title": "PH1", "url": "https://www.producthunt.com/posts/1", "score": 0, "meta": {}},
        ]

        with mock.patch.object(runner, "_fetch_hackernews", return_value=hn_items):
            with mock.patch.object(runner, "_fetch_github_trending", return_value=gh_items):
                with mock.patch.object(runner, "_fetch_reddit", return_value=reddit_items):
                    with mock.patch.object(runner, "_fetch_producthunt", return_value=ph_items):
                        result = runner.run()

        self.assertEqual(result["status"], "completed")
        self.assertTrue((self.project_dir / "hotspots_raw.json").exists())
        self.assertTrue((self.project_dir / "hotspots_summary.json").exists())
        self.assertTrue((self.project_dir / "hotspots_report.md").exists())

        raw = json.loads((self.project_dir / "hotspots_raw.json").read_text(encoding="utf-8"))
        summary = json.loads((self.project_dir / "hotspots_summary.json").read_text(encoding="utf-8"))
        report = (self.project_dir / "hotspots_report.md").read_text(encoding="utf-8")

        self.assertEqual(raw["item_count_raw"], 6)
        self.assertEqual(raw["item_count_deduped"], 5)
        self.assertEqual(summary["item_count"], 5)
        self.assertIn("privacy", raw)
        self.assertTrue(raw["privacy"]["private_keywords_hidden"])
        self.assertIn("TrendR Lite Hotspots Report", report)
        self.assertIn("https://example.com/a", report)

    def test_run_keeps_going_when_one_source_fails(self) -> None:
        template_path = self.project_dir / "template.json"
        private_path = self.project_dir / "private.json"
        write_hotspots_template(template_path, force=True)
        write_hotspots_private_stub(private_path, force=True)

        runner = HotspotsRunner(
            project_dir=self.project_dir,
            topic="Agents",
            per_source_limit=2,
            timeout_sec=5,
            template_path=template_path,
            private_path=private_path,
            session_path=self.project_dir / "session.json",
        )

        with mock.patch.object(runner, "_fetch_hackernews", side_effect=RuntimeError("boom")):
            with mock.patch.object(runner, "_fetch_github_trending", return_value=[]):
                with mock.patch.object(runner, "_fetch_reddit", return_value=[]):
                    with mock.patch.object(runner, "_fetch_producthunt", return_value=[]):
                        result = runner.run()

        self.assertEqual(result["status"], "completed")

        raw = json.loads((self.project_dir / "hotspots_raw.json").read_text(encoding="utf-8"))
        summary = json.loads((self.project_dir / "hotspots_summary.json").read_text(encoding="utf-8"))

        failed_sources = [x for x in raw["source_runs"] if x["status"] == "error"]
        self.assertEqual(len(failed_sources), 1)
        self.assertEqual(failed_sources[0]["source"], "hackernews")
        self.assertIn("boom", failed_sources[0]["error"])
        self.assertEqual(len(summary["sources_failed"]), 1)
        self.assertEqual(summary["sources_failed"][0]["source"], "hackernews")

    def test_private_keywords_are_counted_but_not_persisted_verbatim(self) -> None:
        template_path = self.project_dir / "template.json"
        private_path = self.project_dir / "private.json"
        session_path = self.project_dir / "session.json"

        template = {
            "version": 1,
            "topic": "AI",
            "keywords": ["AI"],
            "platforms": [{"id": "hackernews", "enabled": True}],
        }
        private = {
            "keywords": ["my-personal-tag-123"],
            "session": {"persist": True, "browser_profile": "cdp"},
        }
        template_path.write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")
        private_path.write_text(json.dumps(private, ensure_ascii=False), encoding="utf-8")

        runner = HotspotsRunner(
            project_dir=self.project_dir,
            per_source_limit=2,
            timeout_sec=5,
            template_path=template_path,
            private_path=private_path,
            session_path=session_path,
        )

        with mock.patch.object(
            runner,
            "_fetch_hackernews",
            return_value=[{"source": "hackernews", "title": "AI progress", "url": "https://example.com/ai", "score": 1, "meta": {}}],
        ):
            result = runner.run()

        self.assertEqual(result["status"], "completed")

        raw_path = self.project_dir / "hotspots_raw.json"
        summary_path = self.project_dir / "hotspots_summary.json"
        report_path = self.project_dir / "hotspots_report.md"

        raw_text = raw_path.read_text(encoding="utf-8")
        summary_text = summary_path.read_text(encoding="utf-8")
        report_text = report_path.read_text(encoding="utf-8")

        self.assertNotIn("my-personal-tag-123", raw_text)
        self.assertNotIn("my-personal-tag-123", summary_text)
        self.assertNotIn("my-personal-tag-123", report_text)

        raw = json.loads(raw_text)
        self.assertEqual(raw["keyword_filter"]["private_keyword_count"], 1)

    def test_unknown_platform_is_marked_unsupported(self) -> None:
        template_path = self.project_dir / "template.json"
        private_path = self.project_dir / "private.json"
        session_path = self.project_dir / "session.json"

        template = {
            "version": 1,
            "topic": "AI",
            "keywords": [],
            "platforms": [{"id": "my_custom_platform", "enabled": True}],
        }
        template_path.write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")
        private_path.write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")

        runner = HotspotsRunner(
            project_dir=self.project_dir,
            per_source_limit=2,
            timeout_sec=5,
            template_path=template_path,
            private_path=private_path,
            session_path=session_path,
        )
        result = runner.run()

        self.assertEqual(result["status"], "completed")
        raw = json.loads((self.project_dir / "hotspots_raw.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["source_runs"][0]["source"], "my_custom_platform")
        self.assertEqual(raw["source_runs"][0]["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
