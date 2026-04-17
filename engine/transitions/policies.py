"""Transition policy helpers.

This module hosts policy-level thresholds and helper hooks as we migrate
transition logic out of engine/state_machine.py.
"""


def discovery_params(machine: object) -> tuple[int, int, int, int]:
    """Delegated helper for DISCOVERY threshold normalization."""
    getter = getattr(machine, "_get_discovery_params", None)
    if getter is None:
        raise AttributeError("machine has no _get_discovery_params")
    return getter()
