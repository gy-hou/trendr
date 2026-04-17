"""Heartbeat hooks for coordinator and watchdog integration.

Phase 1 delegates heartbeat writes to ResearchStateMachine internals.
"""

from typing import Any


def send(machine: Any, message: str) -> None:
    sender = getattr(machine, "_send_heartbeat", None)
    if sender is None:
        raise AttributeError("machine has no _send_heartbeat")
    sender(message)
