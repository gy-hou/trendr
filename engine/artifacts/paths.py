"""Artifact path registry."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactPaths:
    project_dir: Path

    @property
    def run_state(self) -> Path:
        return self.project_dir / "run_state.json"

    @property
    def candidates(self) -> Path:
        return self.project_dir / "candidates.csv"

    @property
    def search_log(self) -> Path:
        return self.project_dir / "search_log.md"

    @property
    def notes_dir(self) -> Path:
        return self.project_dir / "notes"

    @property
    def matrix(self) -> Path:
        return self.project_dir / "matrix.csv"

    @property
    def gap_report(self) -> Path:
        return self.project_dir / "gap_report.md"

    @property
    def review(self) -> Path:
        return self.project_dir / "review.md"

    @property
    def references(self) -> Path:
        return self.project_dir / "references.bib"

    @property
    def verify(self) -> Path:
        return self.project_dir / "verify.json"

    @property
    def heartbeat(self) -> Path:
        return self.project_dir / "heartbeat.json"

    @property
    def progress(self) -> Path:
        return self.project_dir / "progress.md"

    @property
    def resume_request(self) -> Path:
        return self.project_dir / "resume_request.json"
