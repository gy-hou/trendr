"""ANALYSIS executor."""


def run(machine: object) -> bool:
    executor = getattr(machine, "_exec_analysis", None)
    if executor is None:
        raise AttributeError("machine has no _exec_analysis")
    return bool(executor())
