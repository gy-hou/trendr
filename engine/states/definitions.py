"""Canonical state names and agent bindings for the research pipeline."""

from typing import Final

INIT: Final[str] = "INIT"
DISCOVERY: Final[str] = "DISCOVERY"
ANALYSIS: Final[str] = "ANALYSIS"
GAP_CHECK: Final[str] = "GAP_CHECK"
WRITING: Final[str] = "WRITING"
VERIFY: Final[str] = "VERIFY"
DONE: Final[str] = "DONE"

VALID_STATES: Final[tuple[str, ...]] = (
    INIT,
    DISCOVERY,
    ANALYSIS,
    GAP_CHECK,
    WRITING,
    VERIFY,
    DONE,
)

STATE_AGENTS: Final[dict[str, str]] = {
    INIT: "orchestrator",
    DISCOVERY: "paper-scout",
    ANALYSIS: "paper-analyzer",
    GAP_CHECK: "orchestrator",
    WRITING: "orchestrator",
    VERIFY: "verifier",
    DONE: "orchestrator",
}
