"""VERIFY executor."""


def run(machine: object) -> bool:
    executor = getattr(machine, "_exec_verify", None)
    if executor is None:
        raise AttributeError("machine has no _exec_verify")
    return bool(executor())
