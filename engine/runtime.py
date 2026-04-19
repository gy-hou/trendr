"""Runtime detection and normalization helpers for TrendR."""

from __future__ import annotations

import os
from typing import Mapping


CANONICAL_RUNTIMES = {"openclaw", "codex", "claude-code", "cli"}
RUNTIME_ALIASES = {
    "claudecode": "claude-code",
}


def normalize_runtime(value: str | None) -> str:
    """Normalize runtime names to canonical values.

    Unknown values fall back to "cli".
    """
    raw = (value or "").strip().lower()
    if not raw:
        return "cli"

    normalized = RUNTIME_ALIASES.get(raw, raw)
    if normalized in CANONICAL_RUNTIMES:
        return normalized
    return "cli"


def detect_runtime(env: Mapping[str, str] | None = None) -> str:
    """Detect runtime with the priority required by TrendR.

    Priority:
    1) TRENDR_PLATFORM           (explicit user override)
    2) OPENCLAW_SESSION_ID
    3) any CODEX_* env key
    4) any CLAUDE_CODE_* env key
    5) cli
    """
    source = env if env is not None else os.environ

    if source.get("TRENDR_PLATFORM"):
        return normalize_runtime(source.get("TRENDR_PLATFORM"))

    if source.get("OPENCLAW_SESSION_ID"):
        return "openclaw"

    if any(k.startswith("CODEX_") for k in source):
        return "codex"

    if any(k.startswith("CLAUDE_CODE_") for k in source):
        return "claude-code"

    return "cli"
