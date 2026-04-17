"""Transition guards.

Phase 1 keeps guard logic inside ResearchStateMachine methods and exposes a
module-level dispatch entrypoint for incremental migration.
"""

from typing import Optional


def check_state_exit(machine: object, current_state: str) -> Optional[str]:
    """Return next state if exit conditions are met.

    This function intentionally delegates to existing private methods in
    phase 1 to keep behavior stable while introducing modular boundaries.
    """
    method_name = {
        "INIT": "_check_init_exit",
        "DISCOVERY": "_check_discovery_exit",
        "ANALYSIS": "_check_analysis_exit",
        "GAP_CHECK": "_check_gap_exit",
        "WRITING": "_check_writing_exit",
        "VERIFY": "_check_verify_exit",
    }.get(current_state)

    if not method_name:
        return None

    checker = getattr(machine, method_name, None)
    if checker is None:
        return None
    return checker()
