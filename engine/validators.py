"""Artifact validators for the TrendR research state machine.

Every state transition requires its exit artifacts to pass validation.
Agents produce files; validators check them before the machine advances.

See ARCHITECTURE.md §1.4 and §3.2 for the full specification.
"""

import csv
import json
import re
from io import StringIO
from pathlib import Path
from typing import Optional


class ValidationResult:
    """Result of an artifact validation check."""

    __slots__ = ("ok", "message", "details")

    def __init__(self, ok: bool, message: str, details: Optional[dict] = None):
        self.ok = ok
        self.message = message
        self.details = details or {}

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        return f"[{status}] {self.message}"


class ArtifactValidator:
    """Validates file contracts before allowing state transitions.

    All methods are static — no instance state needed.
    Each returns a ValidationResult(ok, message, details).
    """

    # ── candidates.csv ──────────────────────────────────────────────

    CANDIDATES_REQUIRED_COLUMNS = {
        "paper_id", "title", "authors", "year",
        "source", "relevance_score",
    }

    @staticmethod
    def validate_candidates_csv(path: Path, min_rows: int = 1) -> ValidationResult:
        """Validate candidates.csv schema and content.

        Args:
            path: Path to candidates.csv
            min_rows: Minimum number of data rows required
        """
        if not path.exists():
            return ValidationResult(False, "candidates.csv not found")

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(False, f"Cannot read candidates.csv: {e}")

        reader = csv.DictReader(StringIO(text))
        headers = set(reader.fieldnames or [])
        missing = ArtifactValidator.CANDIDATES_REQUIRED_COLUMNS - headers
        if missing:
            return ValidationResult(
                False,
                f"Missing columns: {sorted(missing)}",
                {"missing_columns": sorted(missing), "found_columns": sorted(headers)},
            )

        rows = list(reader)
        if len(rows) < min_rows:
            return ValidationResult(
                False,
                f"Only {len(rows)} rows, need >= {min_rows}",
                {"row_count": len(rows), "min_required": min_rows},
            )

        # Check paper_id uniqueness
        ids = [r["paper_id"] for r in rows]
        dupes = [pid for pid in set(ids) if ids.count(pid) > 1]
        if dupes:
            return ValidationResult(
                False,
                f"Duplicate paper_ids: {dupes[:5]}",
                {"duplicate_ids": dupes},
            )

        return ValidationResult(
            True,
            f"{len(rows)} candidates validated",
            {"row_count": len(rows), "sources": list({r.get("source", "?") for r in rows})},
        )

    # ── search_log.md ───────────────────────────────────────────────

    @staticmethod
    def validate_search_log(path: Path) -> ValidationResult:
        """Validate search_log.md has at least one source section."""
        if not path.exists():
            return ValidationResult(False, "search_log.md not found")

        text = path.read_text(encoding="utf-8")
        # Look for markdown headers indicating source sections
        source_sections = re.findall(r"^#{1,3}\s+.*(?:source|search|query)", text, re.MULTILINE | re.IGNORECASE)
        if not source_sections:
            return ValidationResult(
                False,
                "No source/search sections found in search_log.md",
                {"content_length": len(text)},
            )

        return ValidationResult(
            True,
            f"{len(source_sections)} source sections found",
            {"sections": source_sections[:10]},
        )

    # ── notes/{id}.md ───────────────────────────────────────────────

    NOTES_REQUIRED_FRONTMATTER = {"paper_id", "title", "relevance_score"}

    @staticmethod
    def validate_notes_dir(notes_dir: Path, min_count: int = 1) -> ValidationResult:
        """Validate notes directory has enough properly formatted notes.

        Args:
            notes_dir: Path to notes/ directory
            min_count: Minimum number of valid notes required
        """
        if not notes_dir.exists() or not notes_dir.is_dir():
            return ValidationResult(False, "notes/ directory not found")

        md_files = list(notes_dir.glob("*.md"))
        if len(md_files) < min_count:
            return ValidationResult(
                False,
                f"Only {len(md_files)} notes, need >= {min_count}",
                {"note_count": len(md_files), "min_required": min_count},
            )

        valid = 0
        invalid = []
        for f in md_files:
            text = f.read_text(encoding="utf-8")
            # Check YAML frontmatter
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    fm = parts[1]
                    has_fields = all(
                        re.search(rf"^{field}\s*:", fm, re.MULTILINE)
                        for field in ArtifactValidator.NOTES_REQUIRED_FRONTMATTER
                    )
                    if has_fields:
                        valid += 1
                        continue
            invalid.append(f.name)

        if valid < min_count:
            return ValidationResult(
                False,
                f"Only {valid}/{len(md_files)} notes have valid frontmatter (need {min_count})",
                {"valid": valid, "total": len(md_files), "invalid_files": invalid[:10]},
            )

        return ValidationResult(
            True,
            f"{valid} valid notes",
            {"valid": valid, "total": len(md_files)},
        )

    # ── matrix.csv ──────────────────────────────────────────────────

    MATRIX_REQUIRED_COLUMNS = {"paper_id", "method", "dataset", "category"}

    @staticmethod
    def validate_matrix_csv(
        path: Path, candidates_path: Optional[Path] = None
    ) -> ValidationResult:
        """Validate matrix.csv schema and cross-reference with candidates.csv.

        Args:
            path: Path to matrix.csv
            candidates_path: Optional path to candidates.csv for paper_id cross-check
        """
        if not path.exists():
            return ValidationResult(False, "matrix.csv not found")

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(False, f"Cannot read matrix.csv: {e}")

        reader = csv.DictReader(StringIO(text))
        headers = set(reader.fieldnames or [])
        missing = ArtifactValidator.MATRIX_REQUIRED_COLUMNS - headers
        if missing:
            return ValidationResult(
                False,
                f"Missing columns: {sorted(missing)}",
                {"missing_columns": sorted(missing)},
            )

        rows = list(reader)
        if not rows:
            return ValidationResult(False, "matrix.csv is empty")

        # Cross-check paper_ids if candidates.csv available
        if candidates_path and candidates_path.exists():
            cand_reader = csv.DictReader(StringIO(candidates_path.read_text(encoding="utf-8")))
            cand_ids = {r["paper_id"] for r in cand_reader}
            matrix_ids = {r["paper_id"] for r in rows}
            orphans = matrix_ids - cand_ids
            if orphans:
                return ValidationResult(
                    False,
                    f"{len(orphans)} paper_ids in matrix.csv not in candidates.csv",
                    {"orphan_ids": sorted(orphans)[:10]},
                )

        return ValidationResult(
            True,
            f"{len(rows)} matrix entries validated",
            {"row_count": len(rows), "categories": list({r.get("category", "?") for r in rows})},
        )

    # ── gap_report.md ───────────────────────────────────────────────

    @staticmethod
    def validate_gap_report(path: Path) -> ValidationResult:
        """Validate gap_report.md contains a coverage_score line."""
        if not path.exists():
            return ValidationResult(False, "gap_report.md not found")

        text = path.read_text(encoding="utf-8")
        match = re.search(r"coverage_score\s*:\s*([\d.]+)", text)
        if not match:
            return ValidationResult(
                False,
                "No coverage_score: found in gap_report.md",
            )

        try:
            score = float(match.group(1))
        except ValueError:
            return ValidationResult(False, f"Invalid coverage_score value: {match.group(1)}")

        if not (0.0 <= score <= 1.0):
            return ValidationResult(
                False,
                f"coverage_score {score} out of range [0, 1]",
            )

        return ValidationResult(
            True,
            f"coverage_score = {score}",
            {"coverage_score": score},
        )

    @staticmethod
    def get_coverage_score(path: Path) -> Optional[float]:
        """Extract numeric coverage_score from gap_report.md. Returns None on failure."""
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        match = re.search(r"coverage_score\s*:\s*([\d.]+)", text)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    # ── review.md ───────────────────────────────────────────────────

    @staticmethod
    def validate_review_md(path: Path) -> ValidationResult:
        """Validate review.md exists and has reference section."""
        if not path.exists():
            return ValidationResult(False, "review.md not found")

        text = path.read_text(encoding="utf-8")
        if len(text.strip()) < 500:
            return ValidationResult(
                False,
                f"review.md too short ({len(text)} chars)",
                {"char_count": len(text)},
            )

        has_refs = bool(re.search(r"##\s*References", text, re.IGNORECASE)) or \
                   bool(re.search(r"references\.bib", text, re.IGNORECASE))
        if not has_refs:
            return ValidationResult(
                False,
                "review.md has no References section or references.bib link",
            )

        # Count citations
        citations = re.findall(r"\\cite\{([^}]+)\}", text)
        cite_keys = []
        for c in citations:
            cite_keys.extend(k.strip() for k in c.split(","))

        return ValidationResult(
            True,
            f"review.md validated ({len(text)} chars, {len(cite_keys)} citations)",
            {"char_count": len(text), "citation_count": len(cite_keys), "cite_keys": cite_keys},
        )

    # ── references.bib ──────────────────────────────────────────────

    @staticmethod
    def validate_references_bib(
        path: Path, review_path: Optional[Path] = None
    ) -> ValidationResult:
        """Validate references.bib has valid entries and matches review.md citations.

        Args:
            path: Path to references.bib
            review_path: Optional path to review.md for citation cross-check
        """
        if not path.exists():
            return ValidationResult(False, "references.bib not found")

        text = path.read_text(encoding="utf-8")
        # Extract BibTeX entry keys: @article{key, or @inproceedings{key,
        bib_entries = re.findall(r"@\w+\{([^,\s]+)", text)
        if not bib_entries:
            return ValidationResult(False, "No BibTeX entries found in references.bib")

        # Check minimum fields per entry
        entries_text = re.split(r"@\w+\{", text)[1:]  # split by entry start
        incomplete = []
        for i, entry_text in enumerate(entries_text):
            key = bib_entries[i] if i < len(bib_entries) else f"entry_{i}"
            has_title = bool(re.search(r"title\s*=", entry_text, re.IGNORECASE))
            has_author = bool(re.search(r"author\s*=", entry_text, re.IGNORECASE))
            has_year = bool(re.search(r"year\s*=", entry_text, re.IGNORECASE))
            if not (has_title and has_author and has_year):
                missing_fields = []
                if not has_title:
                    missing_fields.append("title")
                if not has_author:
                    missing_fields.append("author")
                if not has_year:
                    missing_fields.append("year")
                incomplete.append({"key": key, "missing": missing_fields})

        # Cross-check with review.md citations
        orphan_cites = []
        if review_path and review_path.exists():
            review_text = review_path.read_text(encoding="utf-8")
            raw_citations = re.findall(r"\\cite\{([^}]+)\}", review_text)
            cite_keys = set()
            for c in raw_citations:
                cite_keys.update(k.strip() for k in c.split(","))
            bib_set = set(bib_entries)
            orphan_cites = sorted(cite_keys - bib_set)

        issues = []
        if incomplete:
            issues.append(f"{len(incomplete)} entries missing required fields")
        if orphan_cites:
            issues.append(f"{len(orphan_cites)} citations not in bib: {orphan_cites[:5]}")

        if orphan_cites:  # citation mismatch is an error
            return ValidationResult(
                False,
                "; ".join(issues),
                {"entries": len(bib_entries), "incomplete": incomplete, "orphan_cites": orphan_cites},
            )

        return ValidationResult(
            True,
            f"{len(bib_entries)} bib entries validated" + (f" ({len(incomplete)} warnings)" if incomplete else ""),
            {"entries": len(bib_entries), "incomplete": incomplete},
        )

    # ── verify.json ─────────────────────────────────────────────────

    @staticmethod
    def validate_verify_json(path: Path) -> ValidationResult:
        """Validate verify.json schema."""
        if not path.exists():
            return ValidationResult(False, "verify.json not found")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return ValidationResult(False, f"verify.json is not valid JSON: {e}")

        if "pass" not in data:
            return ValidationResult(False, "verify.json missing 'pass' field")

        checks = data.get("checks")
        aggregated_issues = None

        if "issues" in data:
            if not isinstance(data["issues"], list):
                return ValidationResult(False, "verify.json 'issues' must be an array")
            aggregated_issues = data["issues"]
        elif checks is not None:
            if not isinstance(checks, dict):
                return ValidationResult(False, "verify.json 'checks' must be an object")

            aggregated_issues = []
            for check_name, check_obj in checks.items():
                if not isinstance(check_obj, dict):
                    continue
                if check_obj.get("pass") is not False:
                    continue

                severity = check_obj.get("severity", "error")
                check_issues = check_obj.get("issues")
                if isinstance(check_issues, list) and check_issues:
                    for issue in check_issues:
                        if isinstance(issue, dict):
                            issue_entry = dict(issue)
                        else:
                            issue_entry = {"reason": str(issue)}
                        issue_entry.setdefault("check", check_name)
                        issue_entry.setdefault("severity", severity)
                        aggregated_issues.append(issue_entry)
                else:
                    aggregated_issues.append(
                        {
                            "check": check_name,
                            "severity": severity,
                            "reason": check_obj.get("details", "failed"),
                        }
                    )
        else:
            return ValidationResult(False, "verify.json missing 'issues' field")

        if not isinstance(aggregated_issues, list):
            return ValidationResult(False, "verify.json 'issues' must be an array")

        if isinstance(checks, dict):
            failed_error_checks = [
                check_name
                for check_name, check_obj in checks.items()
                if isinstance(check_obj, dict)
                and check_obj.get("severity") == "error"
                and check_obj.get("pass") is False
            ]
            if data.get("pass") is True and failed_error_checks:
                return ValidationResult(
                    False,
                    f"pass=true but error-level check failed: {failed_error_checks[0]}",
                    {"failed_error_checks": failed_error_checks},
                )

        return ValidationResult(
            True,
            f"pass={data['pass']}, {len(aggregated_issues)} issues",
            {"pass": data["pass"], "issue_count": len(aggregated_issues)},
        )

    @staticmethod
    def get_verify_pass(path: Path) -> Optional[bool]:
        """Extract the pass/fail boolean from verify.json. Returns None on failure."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("pass")
        except (json.JSONDecodeError, KeyError):
            return None

    # ── run_state.json ──────────────────────────────────────────────

    @staticmethod
    def validate_run_state(path: Path) -> ValidationResult:
        """Validate run_state.json v2 schema."""
        if not path.exists():
            return ValidationResult(False, "run_state.json not found")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return ValidationResult(False, f"run_state.json is not valid JSON: {e}")

        required = {"version", "run_id", "project", "status", "current_state"}
        missing = required - set(data.keys())
        if missing:
            return ValidationResult(
                False,
                f"run_state.json missing fields: {sorted(missing)}",
            )

        valid_states = {"INIT", "DISCOVERY", "ANALYSIS", "GAP_CHECK", "WRITING", "VERIFY", "DONE"}
        if data.get("current_state") not in valid_states:
            return ValidationResult(
                False,
                f"Invalid current_state: {data.get('current_state')}",
            )

        valid_statuses = {"running", "completed", "failed", "paused"}
        if data.get("status") not in valid_statuses:
            return ValidationResult(
                False,
                f"Invalid status: {data.get('status')}",
            )

        return ValidationResult(
            True,
            f"state={data['current_state']}, status={data['status']}",
            {"state": data, "current_state": data["current_state"]},
        )
