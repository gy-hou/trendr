import json
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from engine.verifier import (
    check_bib_quality,
    check_citation_existence,
    check_citation_reality,
    check_claim_support,
    check_coverage,
    check_taxonomy_consistency,
    run_all_checks,
)


class VerifierTestCase(unittest.TestCase):
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

    def write_bib(self, entries: str) -> Path:
        return self.write("references.bib", textwrap.dedent(entries).strip() + "\n")

    def write_note(self, key: str, content: str) -> Path:
        return self.write(f"notes/{key}.md", content)

    def write_review(
        self,
        body: str,
        taxonomy_rows: str | None = None,
        detail_sections: str | None = None,
    ) -> Path:
        taxonomy = taxonomy_rows or (
            "| Category | Description |\n"
            "| --- | --- |\n"
            "| Retrieval Models | Focus on retrieval |\n"
            "| Multi-Agent Systems | Focus on agents |\n"
        )
        details = detail_sections or (
            "### 3.1 Retrieval Models\n"
            "Detailed discussion.\n\n"
            "### 3.2 Multi-Agent Systems\n"
            "Detailed discussion.\n"
        )
        review = textwrap.dedent(
            f"""
            # Review

            {body}

            ## 2. Taxonomy

            {taxonomy}

            ## 3. Detailed Analysis

            {details}

            ## References
            """
        ).strip()
        return self.write("review.md", review + "\n")

    def test_check_citation_existence_success(self) -> None:
        review = self.write_review("Claim one \\cite{paper1}. Claim two \\cite{paper2}.")
        bib = self.write_bib(
            """
            @article{paper1, title={Paper One}, author={Alice}, year={2024}}
            @article{paper2, title={Paper Two}, author={Bob}, year={2023}}
            """
        )

        result = check_citation_existence(review, bib)

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_check_citation_existence_missing_key(self) -> None:
        review = self.write_review("Claim one \\cite{paper1}. Missing \\cite{ghost}.")
        bib = self.write_bib(
            """
            @article{paper1, title={Paper One}, author={Alice}, year={2024}}
            """
        )

        result = check_citation_existence(review, bib)

        self.assertFalse(result["pass"])
        self.assertEqual(result["issues"][0]["citekey"], "ghost")

    def test_check_citation_reality_success_from_candidates(self) -> None:
        bib = self.write_bib(
            """
            @article{paper1, title={Paper One}, author={Alice}, year={2024}}
            """
        )
        candidates = self.write_candidates([
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

        result = check_citation_reality(bib, candidates)

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_check_citation_reality_missing_key_without_api(self) -> None:
        bib = self.write_bib(
            """
            @article{ghost, title={Ghost Paper}, author={Nobody}, year={2024}}
            """
        )
        candidates = self.write_candidates([])

        result = check_citation_reality(bib, candidates, api_check=False)

        self.assertFalse(result["pass"])
        self.assertEqual(result["issues"][0]["citekey"], "ghost")
        self.assertEqual(result["issues"][0]["reason"], "not in candidates.csv")

    def test_check_citation_reality_api_verifies_missing_key(self) -> None:
        bib = self.write_bib(
            """
            @article{ghost, title={Ghost Paper}, author={Nobody}, year={2024}}
            """
        )
        candidates = self.write_candidates([])

        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"paperId": "ghost"}).encode("utf-8")
        response.__exit__.return_value = False

        with mock.patch("engine.verifier.urllib.request.urlopen", return_value=response) as mocked_urlopen:
            with mock.patch("engine.verifier.time.sleep") as mocked_sleep:
                result = check_citation_reality(bib, candidates, api_check=True)

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])
        mocked_urlopen.assert_called_once()
        mocked_sleep.assert_not_called()

    def test_check_claim_support_success(self) -> None:
        review = self.write_review("The retrieval benchmark improves recall and latency \\cite{paper1}.")
        self.write_note(
            "paper1",
            textwrap.dedent(
                """
                ---
                paper_id: paper1
                title: Retrieval Paper
                relevance_score: 5
                ---

                The paper studies retrieval benchmark performance, recall gains, and latency tradeoffs.
                """
            ).strip(),
        )

        result = check_claim_support(review, self.root / "notes")

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_check_claim_support_missing_or_unsupported_note(self) -> None:
        review = self.write_review("The retrieval benchmark improves recall and latency \\cite{paper1}.")
        self.write_note(
            "paper1",
            textwrap.dedent(
                """
                ---
                paper_id: paper1
                title: Retrieval Paper
                relevance_score: 5
                ---

                This note only discusses governance and ethics.
                """
            ).strip(),
        )

        result = check_claim_support(review, self.root / "notes")

        self.assertFalse(result["pass"])
        self.assertEqual(result["issues"][0]["citekey"], "paper1")

    def test_check_claim_support_missing_notes_is_error(self) -> None:
        review = self.write_review("The retrieval benchmark improves recall and latency \\cite{paper1}.")
        (self.root / "notes").mkdir(parents=True, exist_ok=True)

        result = check_claim_support(review, self.root / "notes")

        self.assertFalse(result["pass"])
        self.assertEqual(result["severity"], "error")
        self.assertIn("no .md files", result["details"])

    def test_check_coverage_success(self) -> None:
        review = self.write_review("Strong paper \\cite{paper1}. Secondary paper \\cite{paper2}.")
        candidates = self.write_candidates([
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
                "year": "2024",
                "source": "arxiv",
                "relevance_score": "4",
                "url": "https://example.com/p2",
            },
        ])

        result = check_coverage(review, candidates)

        self.assertTrue(result["pass"])

    def test_check_coverage_missing_high_relevance_paper(self) -> None:
        review = self.write_review("Only one paper is discussed \\cite{paper1}.")
        candidates = self.write_candidates([
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
                "year": "2024",
                "source": "arxiv",
                "relevance_score": "4",
                "url": "https://example.com/p2",
            },
        ])

        result = check_coverage(review, candidates)

        self.assertFalse(result["pass"])
        self.assertEqual(result["issues"][0]["paper_id"], "paper2")

    def test_check_taxonomy_consistency_success(self) -> None:
        review = self.write_review("Claim \\cite{paper1}.")

        result = check_taxonomy_consistency(review)

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_check_taxonomy_consistency_mismatch(self) -> None:
        review = self.write_review(
            "Claim \\cite{paper1}.",
            taxonomy_rows=(
                "| Category | Description |\n"
                "| --- | --- |\n"
                "| Retrieval Models | Focus on retrieval |\n"
            ),
            detail_sections="### 3.1 Agent Coordination\nDiscussion.\n",
        )

        result = check_taxonomy_consistency(review)

        self.assertFalse(result["pass"])
        self.assertGreaterEqual(len(result["issues"]), 1)

    def test_check_bib_quality_success(self) -> None:
        bib = self.write_bib(
            """
            @article{paper1, title={Paper One}, author={Alice}, year={2024}}
            @inproceedings{paper2, title={Paper Two}, author={Bob}, year={2023}}
            """
        )

        result = check_bib_quality(bib)

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_check_bib_quality_missing_fields(self) -> None:
        bib = self.write_bib(
            """
            @article{paper1, title={Paper One}, year={2024}}
            """
        )

        result = check_bib_quality(bib)

        self.assertFalse(result["pass"])
        self.assertIn("author", result["issues"][0]["reason"])

    def test_run_all_checks_aggregates_verify_json(self) -> None:
        review = self.write_review("The retrieval benchmark improves recall and latency \\cite{paper1}.")
        bib = self.write_bib(
            """
            @article{paper1, title={Paper One}, author={Alice}, year={2024}}
            """
        )
        candidates = self.write_candidates([
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
        self.write_note(
            "paper1",
            textwrap.dedent(
                """
                ---
                paper_id: paper1
                title: Retrieval Paper
                relevance_score: 5
                ---

                The paper studies retrieval benchmark performance, recall gains, and latency tradeoffs.
                """
            ).strip(),
        )

        result = run_all_checks(
            review_path=review,
            bib_path=bib,
            candidates_path=candidates,
            notes_dir=self.root / "notes",
            run_id="run-123",
        )

        self.assertTrue(result["pass"])
        self.assertEqual(result["run_id"], "run-123")
        self.assertEqual(set(result["checks"].keys()), {
            "citation_existence",
            "citation_reality",
            "claim_support",
            "coverage",
            "taxonomy_consistency",
            "bib_quality",
        })
        self.assertIn("issues", result)
        self.assertEqual(result["issues"], [])
        self.assertIn("0 errors", result["summary"])


if __name__ == "__main__":
    unittest.main()
