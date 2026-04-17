"""Orchestrator-owned executors (INIT and DONE)."""


def run_init(machine: object) -> bool:
    executor = getattr(machine, "_exec_init", None)
    if executor is None:
        raise AttributeError("machine has no _exec_init")
    return bool(executor())


def run_done(machine: object) -> bool:
    executor = getattr(machine, "_exec_done", None)
    if executor is None:
        raise AttributeError("machine has no _exec_done")
    return bool(executor())
