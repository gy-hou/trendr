import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.validators import ArtifactValidator


class ValidatorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write(self, relative_path: str, content: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_candidates(self, rows: list[dict]) -> Path:
        header = "paper_id,title,authors,year,source,relevance_score,url\n"
        body = "".join(
            f"{row['paper_id']},{row['title']},{row['authors']},{row['year']},"
            f"{row['source']},{row['relevance_score']},{row['url']}\n"
            for row in rows
        )
        return self.write("candidates.csv", header + body)

    def write_matrix(self, rows: list[dict], header: str | None = None) -> Path:
        header = header or "paper_id,method,dataset,category\n"
        body = "".join(
            f"{row['paper_id']},{row['method']},{row['dataset']},{row['category']}\n"
            for row in rows
        )
        return self.write("matrix.csv", header + body)

    def write_note(self, filename: str, frontmatter: dict[str, str], body: str = "Body") -> Path:
        fields = "\n".join(f"{key}: {value}" for key, value in frontmatter.items())
        content = f"---\n{fields}\n---\n\n{body}\n"
        return self.write(f"notes/{filename}", content)

    def write_review(self, with_references: bool = True, citations: str = "\\cite{paper1}") -> Path:
        body = ("TrendR review content. " * 40).strip()
        references = "\n\n## References\n\n- Example entry\n" if with_references else ""
        content = f"# Review\n\n{body}\n\n{citations}{references}\n"
        return self.write("review.md", content)

    def test_validate_candidates_csv_success(self) -> None:
        path = self.write_candidates([
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
        ])

        result = ArtifactValidator.validate_candidates_csv(path, min_rows=2)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["row_count"], 2)

    def test_validate_candidates_csv_success_with_v2_rich_schema(self) -> None:
        path = self.write(
            "candidates.csv",
            textwrap.dedent(
                """
                paper_id,title,authors,year,source,venue,citation_count,relevance_score,has_code,abstract_snippet
                paper1,Paper One,Alice,2024,arxiv,arXiv,10,5,unknown,Snippet one
                paper2,Paper Two,Bob,2025,openalex,NeurIPS,3,4,yes,Snippet two
                """
            ).strip()
            + "\n",
        )

        result = ArtifactValidator.validate_candidates_csv(path, min_rows=2)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["row_count"], 2)

    def test_validate_candidates_csv_missing_columns(self) -> None:
        path = self.write(
            "candidates.csv",
            "paper_id,title,year\npaper1,Paper One,2024\n",
        )

        result = ArtifactValidator.validate_candidates_csv(path)

        self.assertFalse(result.ok)
        self.assertIn("authors", result.details["missing_columns"])

    def test_validate_candidates_csv_empty_file(self) -> None:
        path = self.write("candidates.csv", "")

        result = ArtifactValidator.validate_candidates_csv(path)

        self.assertFalse(result.ok)
        self.assertIn("Missing columns", result.message)

    def test_validate_candidates_csv_duplicate_paper_id(self) -> None:
        path = self.write_candidates([
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
                "paper_id": "paper1",
                "title": "Paper One Copy",
                "authors": "Alice",
                "year": "2024",
                "source": "arxiv",
                "relevance_score": "4",
                "url": "https://example.com/p1b",
            },
        ])

        result = ArtifactValidator.validate_candidates_csv(path, min_rows=2)

        self.assertFalse(result.ok)
        self.assertIn("paper1", result.details["duplicate_ids"])

    def test_validate_candidates_csv_min_rows_not_met(self) -> None:
        path = self.write_candidates([
            {
                "paper_id": "paper1",
                "title": "Paper One",
                "authors": "Alice",
                "year": "2024",
                "source": "arxiv",
                "relevance_score": "5",
                "url": "https://example.com/p1",
            }
        ])

        result = ArtifactValidator.validate_candidates_csv(path, min_rows=2)

        self.assertFalse(result.ok)
        self.assertEqual(result.details["row_count"], 1)

    def test_validate_search_log_success(self) -> None:
        path = self.write(
            "search_log.md",
            textwrap.dedent(
                """
                # Search Strategy

                ## Source Query: arXiv
                - topic: TrendR
                """
            ).strip(),
        )

        result = ArtifactValidator.validate_search_log(path)

        self.assertTrue(result.ok)
        self.assertEqual(len(result.details["sections"]), 2)

    def test_validate_search_log_without_source_section(self) -> None:
        path = self.write(
            "search_log.md",
            textwrap.dedent(
                """
                # Notes

                ## Summary
                - No concrete source sections here.
                """
            ).strip(),
        )

        result = ArtifactValidator.validate_search_log(path)

        self.assertFalse(result.ok)

    def test_validate_notes_dir_success(self) -> None:
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        self.write_note(
            "paper1.md",
            {
                "paper_id": "paper1",
                "title": "Paper One",
                "relevance_score": "5",
            },
        )

        result = ArtifactValidator.validate_notes_dir(notes_dir)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["valid"], 1)

    def test_validate_notes_dir_empty_directory(self) -> None:
        notes_dir = self.root / "notes"
        notes_dir.mkdir()

        result = ArtifactValidator.validate_notes_dir(notes_dir)

        self.assertFalse(result.ok)
        self.assertEqual(result.details["note_count"], 0)

    def test_validate_notes_dir_missing_frontmatter_field(self) -> None:
        notes_dir = self.root / "notes"
        notes_dir.mkdir()
        self.write_note(
            "paper1.md",
            {
                "paper_id": "paper1",
                "title": "Paper One",
            },
        )

        result = ArtifactValidator.validate_notes_dir(notes_dir)

        self.assertFalse(result.ok)
        self.assertIn("paper1.md", result.details["invalid_files"])

    def test_validate_matrix_csv_success(self) -> None:
        path = self.write_matrix([
            {
                "paper_id": "paper1",
                "method": "survey",
                "dataset": "demo",
                "category": "analysis",
            }
        ])
        candidates_path = self.write_candidates([
            {
                "paper_id": "paper1",
                "title": "Paper One",
                "authors": "Alice",
                "year": "2024",
                "source": "arxiv",
                "relevance_score": "5",
                "url": "https://example.com/p1",
            }
        ])

        result = ArtifactValidator.validate_matrix_csv(path, candidates_path)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["row_count"], 1)

    def test_validate_matrix_csv_missing_columns(self) -> None:
        path = self.write(
            "matrix.csv",
            "paper_id,method,category\npaper1,survey,analysis\n",
        )

        result = ArtifactValidator.validate_matrix_csv(path)

        self.assertFalse(result.ok)
        self.assertIn("dataset", result.details["missing_columns"])

    def test_validate_matrix_csv_orphan_paper_id(self) -> None:
        path = self.write_matrix([
            {
                "paper_id": "paper2",
                "method": "survey",
                "dataset": "demo",
                "category": "analysis",
            }
        ])
        candidates_path = self.write_candidates([
            {
                "paper_id": "paper1",
                "title": "Paper One",
                "authors": "Alice",
                "year": "2024",
                "source": "arxiv",
                "relevance_score": "5",
                "url": "https://example.com/p1",
            }
        ])

        result = ArtifactValidator.validate_matrix_csv(path, candidates_path)

        self.assertFalse(result.ok)
        self.assertIn("paper2", result.details["orphan_ids"])

    def test_validate_gap_report_success(self) -> None:
        path = self.write(
            "gap_report.md",
            "# Gap Report\n\ncoverage_score: 0.82\n",
        )

        result = ArtifactValidator.validate_gap_report(path)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["coverage_score"], 0.82)

    def test_validate_gap_report_without_coverage_score(self) -> None:
        path = self.write("gap_report.md", "# Gap Report\n\nNo score available.\n")

        result = ArtifactValidator.validate_gap_report(path)

        self.assertFalse(result.ok)

    def test_validate_gap_report_out_of_range_score(self) -> None:
        path = self.write("gap_report.md", "coverage_score: 1.5\n")

        result = ArtifactValidator.validate_gap_report(path)

        self.assertFalse(result.ok)
        self.assertIn("out of range", result.message)

    def test_validate_review_md_success(self) -> None:
        path = self.write_review(with_references=True)

        result = ArtifactValidator.validate_review_md(path)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["citation_count"], 1)

    def test_validate_review_md_too_short(self) -> None:
        path = self.write("review.md", "# Review\n\nToo short.\n\n## References\n")

        result = ArtifactValidator.validate_review_md(path)

        self.assertFalse(result.ok)
        self.assertIn("too short", result.message)

    def test_validate_review_md_without_references_section(self) -> None:
        path = self.write_review(with_references=False)

        result = ArtifactValidator.validate_review_md(path)

        self.assertFalse(result.ok)
        self.assertIn("References", result.message)

    def test_validate_references_bib_success(self) -> None:
        path = self.write(
            "references.bib",
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
        review_path = self.write_review(with_references=True, citations="\\cite{paper1}")

        result = ArtifactValidator.validate_references_bib(path, review_path)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["entries"], 1)

    def test_validate_references_bib_missing_required_fields(self) -> None:
        path = self.write(
            "references.bib",
            textwrap.dedent(
                """
                @article{paper1,
                  title={Paper One},
                  year={2024}
                }
                """
            ).strip(),
        )

        result = ArtifactValidator.validate_references_bib(path)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["incomplete"][0]["key"], "paper1")
        self.assertIn("author", result.details["incomplete"][0]["missing"])

    def test_validate_references_bib_citation_mismatch(self) -> None:
        path = self.write(
            "references.bib",
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
        review_path = self.write_review(with_references=True, citations="\\cite{paper2}")

        result = ArtifactValidator.validate_references_bib(path, review_path)

        self.assertFalse(result.ok)
        self.assertIn("paper2", result.details["orphan_cites"])

    def test_validate_verify_json_success(self) -> None:
        path = self.write(
            "verify.json",
            json.dumps({"pass": True, "issues": []}),
        )

        result = ArtifactValidator.validate_verify_json(path)

        self.assertTrue(result.ok)
        self.assertTrue(result.details["pass"])

    def test_validate_verify_json_success_without_top_level_issues(self) -> None:
        path = self.write(
            "verify.json",
            json.dumps(
                {
                    "pass": True,
                    "summary": "0 errors, 1 warning",
                    "checks": {
                        "citation_existence": {
                            "pass": True,
                            "severity": "error",
                            "details": "ok",
                        },
                        "bib_quality": {
                            "pass": False,
                            "severity": "warning",
                            "details": "4 entries bad",
                            "issues": [{"citekey": "x", "reason": "no author"}],
                        },
                    },
                }
            ),
        )

        result = ArtifactValidator.validate_verify_json(path)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["issue_count"], 1)

    def test_validate_verify_json_fails_when_error_check_conflicts_with_pass(self) -> None:
        path = self.write(
            "verify.json",
            json.dumps(
                {
                    "pass": True,
                    "issues": [],
                    "checks": {
                        "citation_existence": {
                            "pass": False,
                            "severity": "error",
                            "details": "missing 3",
                        }
                    },
                }
            ),
        )

        result = ArtifactValidator.validate_verify_json(path)

        self.assertFalse(result.ok)
        self.assertIn("pass=true but error-level check failed", result.message)

    def test_validate_verify_json_invalid_json(self) -> None:
        path = self.write("verify.json", "{this is not valid json}")

        result = ArtifactValidator.validate_verify_json(path)

        self.assertFalse(result.ok)
        self.assertIn("not valid JSON", result.message)

    def test_validate_verify_json_missing_fields(self) -> None:
        path = self.write(
            "verify.json",
            json.dumps({"pass": True}),
        )

        result = ArtifactValidator.validate_verify_json(path)

        self.assertFalse(result.ok)
        self.assertIn("missing 'issues'", result.message)


if __name__ == "__main__":
    unittest.main()
