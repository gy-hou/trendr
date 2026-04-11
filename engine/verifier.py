"""Executable verification checks for TrendR v2 reviews.

These checks turn the verifier skill's markdown rules into stdlib-only Python.
Each check returns a dict shaped like a single entry in verify.json.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "our", "that",
    "the", "their", "this", "those", "these", "to", "was", "were", "with",
    "we", "show", "shows", "shown", "study", "studies", "paper", "papers",
    "review", "section", "using", "used", "than", "then", "also", "such",
    "can", "may", "via", "not", "more", "most", "less", "few",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _result(severity: str, passed: bool, details: str, issues: list[dict] | None = None) -> dict:
    return {
        "pass": passed,
        "severity": severity,
        "details": details,
        "issues": issues or [],
    }


def _missing_input(severity: str, missing: Iterable[Path]) -> dict:
    paths = [str(Path(p)) for p in missing]
    issues = [{"path": path, "reason": "missing input"} for path in paths]
    return _result(severity, False, f"Missing required inputs: {', '.join(paths)}", issues)


def _read_text(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _read_csv_rows(path: Path | str) -> list[dict]:
    return list(csv.DictReader(StringIO(_read_text(path))))


def _extract_cite_keys(text: str) -> list[str]:
    keys: list[str] = []
    for group in re.findall(r"\\cite[a-zA-Z*]*\{([^}]+)\}", text):
        keys.extend(key.strip() for key in group.split(",") if key.strip())
    return keys


def _extract_bib_entries(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"@\w+\{([^,\s]+)\s*,", text))
    entries: dict[str, str] = {}
    for index, match in enumerate(matches):
        key = match.group(1)
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[key] = text[start:end]
    return entries


def _normalize_label(value: str) -> str:
    value = re.sub(r"[`*_]", "", value)
    value = re.sub(r"^\d+(?:\.\d+)*\s*[-:.]?\s*", "", value.strip())
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


def _extract_section(text: str, heading: str) -> str | None:
    match = re.search(rf"^\s*##\s*(?:\d+\.\s*)?{heading}\b.*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    rest = text[match.end():]
    next_heading = re.search(r"^\s*##\s+", rest, re.MULTILINE)
    if next_heading:
        return rest[:next_heading.start()]
    return rest


def _extract_note_index(notes_dir: Path | str) -> dict[str, str]:
    notes_path = Path(notes_dir)
    note_index: dict[str, str] = {}
    if not notes_path.exists() or not notes_path.is_dir():
        return note_index

    for note_file in notes_path.glob("*.md"):
        text = note_file.read_text(encoding="utf-8")
        note_index[note_file.stem] = text
        frontmatter = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
        if frontmatter:
            match = re.search(r"^paper_id\s*:\s*(.+)$", frontmatter.group(1), re.MULTILINE)
            if match:
                note_index[match.group(1).strip()] = text
    return note_index


def _split_sentences(text: str) -> list[str]:
    raw_parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    return [part.strip() for part in raw_parts if part.strip()]


def _tokenize_keywords(text: str) -> set[str]:
    text = re.sub(r"\\cite[a-zA-Z*]*\{[^}]+\}", " ", text)
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", text.lower())
    return {token for token in tokens if token not in STOPWORDS}


def _fetch_semantic_scholar_paper(paper_id: str) -> tuple[bool, str]:
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/"
        f"{urllib.parse.quote(paper_id, safe='')}"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "TrendR/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
        data = json.loads(payload or "{}")
        if isinstance(data, dict) and data:
            return True, "verified via Semantic Scholar"
        return False, "Semantic Scholar returned empty payload"
    except urllib.error.HTTPError as exc:
        return False, f"Semantic Scholar returned {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"Semantic Scholar request failed: {exc.reason}"
    except json.JSONDecodeError:
        return False, "Semantic Scholar returned invalid JSON"


def check_citation_existence(review_path: Path | str, bib_path: Path | str) -> dict:
    review_path = Path(review_path)
    bib_path = Path(bib_path)
    missing_inputs = [path for path in (review_path, bib_path) if not path.exists()]
    if missing_inputs:
        return _missing_input("error", missing_inputs)

    cite_keys = _extract_cite_keys(_read_text(review_path))
    bib_keys = set(_extract_bib_entries(_read_text(bib_path)))
    missing_keys = sorted(set(cite_keys) - bib_keys)
    issues = [
        {"citekey": key, "reason": "missing from references.bib"}
        for key in missing_keys
    ]
    found = len(set(cite_keys)) - len(missing_keys)
    total = len(set(cite_keys))
    details = f"{found}/{total} citation keys found in references.bib"
    return _result("error", not missing_keys, details, issues)


def check_citation_reality(
    bib_path: Path | str,
    candidates_path: Path | str,
    api_check: bool = False,
) -> dict:
    bib_path = Path(bib_path)
    candidates_path = Path(candidates_path)
    missing_inputs = [path for path in (bib_path, candidates_path) if not path.exists()]
    if missing_inputs:
        return _missing_input("error", missing_inputs)

    bib_keys = sorted(_extract_bib_entries(_read_text(bib_path)))
    candidate_ids = {
        row.get("paper_id", "").strip()
        for row in _read_csv_rows(candidates_path)
        if row.get("paper_id", "").strip()
    }

    issues: list[dict] = []
    verified_via_api = 0
    missing_from_candidates = [key for key in bib_keys if key not in candidate_ids]

    if api_check:
        for index, key in enumerate(missing_from_candidates):
            if index > 0:
                time.sleep(1)
            exists, reason = _fetch_semantic_scholar_paper(key)
            if exists:
                verified_via_api += 1
            else:
                issues.append({"citekey": key, "reason": reason})
    else:
        issues.extend(
            {"citekey": key, "reason": "not in candidates.csv"}
            for key in missing_from_candidates
        )

    verified_count = len(bib_keys) - len(missing_from_candidates) + verified_via_api
    details = (
        f"{verified_count}/{len(bib_keys)} bib entries found in candidates.csv"
        + (" or verified via Semantic Scholar" if api_check else "")
    )
    return _result("error", not issues, details, issues)


def check_claim_support(review_path: Path | str, notes_dir: Path | str) -> dict:
    review_path = Path(review_path)
    notes_dir = Path(notes_dir)
    missing_inputs = [path for path in (review_path, notes_dir) if not path.exists()]
    if missing_inputs:
        return _missing_input("error", missing_inputs)

    review_text = _read_text(review_path)
    note_files = list(notes_dir.glob("*.md"))
    if not note_files:
        cite_keys = sorted(set(_extract_cite_keys(review_text)))
        issues = [
            {"citekey": key, "reason": "notes/*.md missing (notes directory has no markdown files)"}
            for key in cite_keys
        ]
        if not issues:
            issues = [{"reason": "notes directory has no markdown files"}]
        return _result(
            "error",
            False,
            "notes directory has no .md files; claim-to-note tracing not possible",
            issues,
        )

    note_index = _extract_note_index(notes_dir)
    citation_sentences = [sentence for sentence in _split_sentences(review_text) if "\\cite" in sentence]

    total_claims = 0
    supported_claims = 0
    issues: list[dict] = []
    missing_note_issues = 0

    for sentence in citation_sentences:
        sentence_keys = _extract_cite_keys(sentence)
        claim_keywords = _tokenize_keywords(sentence)
        threshold = 1 if len(claim_keywords) <= 3 else 2

        for key in sentence_keys:
            total_claims += 1
            note_text = note_index.get(key)
            if note_text is None:
                issues.append({
                    "citekey": key,
                    "reason": "supporting note not found",
                    "sentence": sentence,
                })
                missing_note_issues += 1
                continue

            overlap = sorted(claim_keywords & _tokenize_keywords(note_text))
            if len(overlap) >= threshold:
                supported_claims += 1
                continue

            issues.append({
                "citekey": key,
                "reason": "insufficient keyword overlap with note",
                "sentence": sentence,
                "overlap": overlap,
            })

    if total_claims == 0:
        return _result("warning", True, "No citation-backed claims found in review.md", [])

    details = f"{supported_claims}/{total_claims} citation-backed claims have supporting notes"
    severity = "error" if missing_note_issues > 0 else "warning"
    return _result(severity, not issues, details, issues)


def check_coverage(
    review_path: Path | str,
    candidates_path: Path | str,
    min_relevance: int = 4,
) -> dict:
    review_path = Path(review_path)
    candidates_path = Path(candidates_path)
    missing_inputs = [path for path in (review_path, candidates_path) if not path.exists()]
    if missing_inputs:
        return _missing_input("warning", missing_inputs)

    cited_keys = set(_extract_cite_keys(_read_text(review_path)))
    relevant_ids = set()
    for row in _read_csv_rows(candidates_path):
        paper_id = row.get("paper_id", "").strip()
        score_raw = row.get("relevance_score", "").strip()
        if not paper_id:
            continue
        try:
            if float(score_raw) >= min_relevance:
                relevant_ids.add(paper_id)
        except ValueError:
            continue

    missing_coverage = sorted(relevant_ids - cited_keys)
    issues = [{"paper_id": key, "reason": "high-relevance paper not cited"} for key in missing_coverage]
    details = f"{len(relevant_ids) - len(missing_coverage)}/{len(relevant_ids)} relevance>={min_relevance} papers cited"
    return _result("warning", not missing_coverage, details, issues)


def check_taxonomy_consistency(review_path: Path | str) -> dict:
    review_path = Path(review_path)
    if not review_path.exists():
        return _missing_input("error", [review_path])

    review_text = _read_text(review_path)
    taxonomy_section = _extract_section(review_text, "Taxonomy")
    analysis_section = _extract_section(review_text, "Detailed Analysis")

    if taxonomy_section is None or analysis_section is None:
        missing_sections = []
        if taxonomy_section is None:
            missing_sections.append({"section": "Taxonomy", "reason": "section not found"})
        if analysis_section is None:
            missing_sections.append({"section": "Detailed Analysis", "reason": "section not found"})
        return _result("error", False, "Required review sections are missing", missing_sections)

    table_lines = [line.strip() for line in taxonomy_section.splitlines() if "|" in line]
    if len(table_lines) < 2:
        return _result("error", False, "Taxonomy table not found or incomplete", [{"reason": "taxonomy table missing"}])

    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    try:
        category_index = next(
            index for index, cell in enumerate(header)
            if _normalize_label(cell) == "category"
        )
    except StopIteration:
        return _result("error", False, "Taxonomy table has no Category column", [{"reason": "missing Category column"}])

    categories = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if category_index < len(cells) and cells[category_index]:
            categories.append(_normalize_label(cells[category_index]))

    analysis_headers = [
        _normalize_label(match.group(1))
        for match in re.finditer(
            r"^\s*###\s*(?:\d+(?:\.\d+)*\s*[-:.]?\s*)?(.*?)\s*$",
            analysis_section,
            re.MULTILINE,
        )
    ]

    category_set = {value for value in categories if value}
    analysis_set = {value for value in analysis_headers if value}

    missing_in_analysis = sorted(category_set - analysis_set)
    missing_in_taxonomy = sorted(analysis_set - category_set)
    issues = (
        [{"category": value, "reason": "present in taxonomy table but missing in analysis headings"} for value in missing_in_analysis]
        + [{"category": value, "reason": "present in analysis headings but missing in taxonomy table"} for value in missing_in_taxonomy]
    )
    passed = not issues and len(category_set) == len(analysis_set)
    details = f"{len(category_set)} taxonomy categories match {len(analysis_set)} analysis section headers"
    return _result("error", passed, details, issues)


def check_bib_quality(bib_path: Path | str) -> dict:
    bib_path = Path(bib_path)
    if not bib_path.exists():
        return _missing_input("warning", [bib_path])

    entries = _extract_bib_entries(_read_text(bib_path))
    if not entries:
        return _result("warning", False, "No BibTeX entries found", [{"reason": "references.bib contains no entries"}])

    issues = []
    complete = 0
    for key, entry_text in entries.items():
        missing_fields = []
        for field in ("title", "author", "year"):
            if not re.search(rf"\b{field}\s*=", entry_text, re.IGNORECASE):
                missing_fields.append(field)
        if missing_fields:
            issues.append({"citekey": key, "reason": f"missing fields: {', '.join(missing_fields)}"})
        else:
            complete += 1

    details = f"{complete}/{len(entries)} entries have required fields"
    return _result("warning", not issues, details, issues)


def run_all_checks(
    review_path: Path | str,
    bib_path: Path | str,
    candidates_path: Path | str,
    notes_dir: Path | str,
    run_id: str | None = None,
    api_check: bool = False,
    min_relevance: int = 4,
) -> dict:
    checks = {
        "citation_existence": check_citation_existence(review_path, bib_path),
        "citation_reality": check_citation_reality(bib_path, candidates_path, api_check=api_check),
        "claim_support": check_claim_support(review_path, notes_dir),
        "coverage": check_coverage(review_path, candidates_path, min_relevance=min_relevance),
        "taxonomy_consistency": check_taxonomy_consistency(review_path),
        "bib_quality": check_bib_quality(bib_path),
    }

    error_failures = sum(1 for result in checks.values() if result["severity"] == "error" and not result["pass"])
    warning_failures = sum(1 for result in checks.values() if result["severity"] == "warning" and not result["pass"])

    flattened_issues: list[dict] = []
    for check_name, check_result in checks.items():
        if check_result.get("pass") is not False:
            continue
        severity = check_result.get("severity", "error")
        check_issues = check_result.get("issues")
        if isinstance(check_issues, list) and check_issues:
            for issue in check_issues:
                if isinstance(issue, dict):
                    issue_entry = dict(issue)
                else:
                    issue_entry = {"reason": str(issue)}
                issue_entry.setdefault("check", check_name)
                issue_entry.setdefault("severity", severity)
                flattened_issues.append(issue_entry)
        else:
            flattened_issues.append(
                {
                    "check": check_name,
                    "severity": severity,
                    "reason": check_result.get("details", "failed"),
                }
            )

    return {
        "pass": error_failures == 0,
        "run_id": run_id,
        "checked_at": _now_iso(),
        "summary": f"{error_failures} errors, {warning_failures} warnings",
        "issues": flattened_issues,
        "checks": checks,
    }


__all__ = [
    "check_bib_quality",
    "check_citation_existence",
    "check_citation_reality",
    "check_claim_support",
    "check_coverage",
    "check_taxonomy_consistency",
    "run_all_checks",
]
