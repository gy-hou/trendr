"""WRITING executor."""


def run(machine: object) -> bool:
    executor = getattr(machine, "_exec_writing", None)
    if executor is None:
        raise AttributeError("machine has no _exec_writing")
    return bool(executor())
