"""State-machine configuration constants.

This module exists so policy and timeout values can be maintained outside
engine/state_machine.py.
"""

from typing import Final

from .definitions import (
    ANALYSIS,
    DISCOVERY,
    DONE,
    GAP_CHECK,
    INIT,
    VERIFY,
    WRITING,
)

DEFAULT_COVERAGE_THRESHOLD: Final[float] = 0.7
DEFAULT_MAX_DISCOVERY_ROUNDS: Final[int] = 6
DEFAULT_MIN_DISCOVERY_ROUNDS: Final[int] = 1
DEFAULT_MAX_FIX_ROUNDS: Final[int] = 2
DEFAULT_FALLBACK_ANALYSIS_ROWS: Final[int] = 20

STATE_TIMEOUTS: Final[dict[str, int]] = {
    INIT: 60,
    DISCOVERY: 900,
    ANALYSIS: 1200,
    GAP_CHECK: 300,
    WRITING: 1800,
    VERIFY: 600,
    DONE: 60,
}

PROGRESS_MAP: Final[dict[str, tuple[int, int]]] = {
    INIT: (0, 5),
    DISCOVERY: (5, 40),
    ANALYSIS: (40, 75),
    GAP_CHECK: (75, 85),
    WRITING: (85, 97),
    VERIFY: (97, 99),
    DONE: (100, 100),
}
