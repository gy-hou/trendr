"""File-contract access layer for state transitions."""

from pathlib import Path

from engine.validators import ArtifactValidator, ValidationResult


class ArtifactContracts:
    """Thin wrapper around ArtifactValidator for modular engine wiring."""

    def __init__(self) -> None:
        self.validator = ArtifactValidator()

    def run_state(self, path: Path) -> ValidationResult:
        return self.validator.validate_run_state(path)

    def candidates(self, path: Path, min_rows: int = 1) -> ValidationResult:
        return self.validator.validate_candidates_csv(path, min_rows=min_rows)

    def matrix(self, path: Path, candidates_path: Path) -> ValidationResult:
        return self.validator.validate_matrix_csv(path, candidates_path)

    def notes(self, notes_dir: Path, min_count: int = 1) -> ValidationResult:
        return self.validator.validate_notes_dir(notes_dir, min_count=min_count)

    def gap_report(self, path: Path) -> ValidationResult:
        return self.validator.validate_gap_report(path)

    def review(self, review_path: Path) -> ValidationResult:
        return self.validator.validate_review_md(review_path)

    def references(self, bib_path: Path, review_path: Path) -> ValidationResult:
        return self.validator.validate_references_bib(bib_path, review_path)

    def verify(self, path: Path) -> ValidationResult:
        return self.validator.validate_verify_json(path)
