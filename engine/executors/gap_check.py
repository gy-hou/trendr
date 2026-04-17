"""GAP_CHECK executor."""


def run(machine: object) -> bool:
    executor = getattr(machine, "_exec_gap_check", None)
    if executor is None:
        raise AttributeError("machine has no _exec_gap_check")
    return bool(executor())
