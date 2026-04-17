"""Transition rule dispatcher."""

from typing import Optional

from .guards import check_state_exit


def next_state(machine: object) -> Optional[str]:
    """Compute next state from machine.current_state using guard checks."""
    state = getattr(machine, "state", None)
    if not state:
        return None
    current = state.get("current_state")
    if not current:
        return None
    return check_state_exit(machine, current)
