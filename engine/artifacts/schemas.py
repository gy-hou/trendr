"""Artifact schema constants used by contracts and evaluation."""

CANDIDATES_REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "authors",
    "year",
    "source",
    "relevance_score",
)

MATRIX_REQUIRED_COLUMNS = (
    "paper_id",
    "method",
    "dataset",
    "category",
)

VERIFY_REQUIRED_FIELDS = (
    "pass",
    "issues",
    "citation_check",
    "claim_check",
)
