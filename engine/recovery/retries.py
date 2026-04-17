"""Retry bookkeeping helpers."""


def increment_fix_round(state: dict, max_fix_rounds: int) -> bool:
    """Increment fix_rounds when under cap.

    Returns True when incremented, False when limit reached.
    """
    current = int(state.get("fix_rounds", 0) or 0)
    if current >= max_fix_rounds:
        return False
    state["fix_rounds"] = current + 1
    return True
