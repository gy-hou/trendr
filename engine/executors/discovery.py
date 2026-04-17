"""DISCOVERY executor."""


def run(machine: object) -> bool:
    executor = getattr(machine, "_exec_discovery", None)
    if executor is None:
        raise AttributeError("machine has no _exec_discovery")
    return bool(executor())
