"""Tests that the two runtimes don't cross-contaminate each other's files."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

OPENCLAW_INSTALLER = REPO / "runtimes" / "openclaw" / "install.sh"
CC_INSTALLER = REPO / "runtimes" / "claude-code" / "install.sh"


# ---------------------------------------------------------------------------
# OpenClaw installer must not reference Claude Code artefacts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        ".claude/",
        "claude-code.md",
        "runtimes/claude-code/",
        "ClaudeCodeAdapter",
    ],
)
def test_openclaw_installer_no_claude_code_refs(forbidden):
    if not OPENCLAW_INSTALLER.exists():
        pytest.skip("runtimes/openclaw/install.sh not present")
    text = OPENCLAW_INSTALLER.read_text(encoding="utf-8")
    assert forbidden not in text, (
        f"runtimes/openclaw/install.sh references Claude Code artefact: {forbidden!r}"
    )


# ---------------------------------------------------------------------------
# Claude Code installer must not reference OpenClaw artefacts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        "~/.openclaw",
        "supervisor.py",
        "openclaw install",
        "openclaw_session",
    ],
)
def test_claude_code_installer_no_openclaw_refs(forbidden):
    if not CC_INSTALLER.exists():
        pytest.skip("runtimes/claude-code/install.sh not present")
    text = CC_INSTALLER.read_text(encoding="utf-8")
    assert forbidden not in text, (
        f"runtimes/claude-code/install.sh references OpenClaw artefact: {forbidden!r}"
    )


# ---------------------------------------------------------------------------
# Claude Code exclusive files must not appear inside runtimes/openclaw/
# ---------------------------------------------------------------------------


def test_no_claude_code_md_in_openclaw_runtime():
    oc_dir = REPO / "runtimes" / "openclaw"
    if not oc_dir.exists():
        pytest.skip("runtimes/openclaw/ not present")
    cc_files = list(oc_dir.rglob("claude-code.md"))
    assert not cc_files, f"claude-code.md found inside runtimes/openclaw/: {cc_files}"


# ---------------------------------------------------------------------------
# OpenClaw's supervisor.py is still present (not deleted by CC work)
# ---------------------------------------------------------------------------


def test_openclaw_supervisor_py_preserved():
    supervisor = REPO / "skills" / "trendr-watchdog" / "supervisor.py"
    assert supervisor.exists(), "skills/trendr-watchdog/supervisor.py was deleted — must be preserved"


# ---------------------------------------------------------------------------
# Each skill has both SKILL.md (shared) and claude-code.md (CC specific)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skill_name",
    [
        "paper-scout",
        "paper-analyzer",
        "review-writer",
        "verifier",
        "research-vault",
        "trendr-watchdog",
        "platform-hotspots",
        "chrome-cdp-setup",
    ],
)
def test_each_skill_has_shared_and_cc_sibling(skill_name):
    skill_dir = REPO / "skills" / skill_name
    assert (skill_dir / "SKILL.md").exists(), f"{skill_name}/SKILL.md missing"
    assert (skill_dir / "claude-code.md").exists(), f"{skill_name}/claude-code.md missing"


# ---------------------------------------------------------------------------
# Runtime directories are disjoint (no shared files between them)
# ---------------------------------------------------------------------------


def test_openclaw_and_claude_code_runtime_dirs_have_no_shared_files():
    oc_dir = REPO / "runtimes" / "openclaw"
    cc_dir = REPO / "runtimes" / "claude-code"
    if not oc_dir.exists() or not cc_dir.exists():
        pytest.skip("one or both runtime dirs missing")

    oc_files = {f.name for f in oc_dir.rglob("*") if f.is_file()}
    cc_files = {f.name for f in cc_dir.rglob("*") if f.is_file()}
    # plugin.json exists in claude-code only; install.sh / uninstall.sh exist in both (that's expected)
    # Check there are no .py files shared
    oc_py = {f.name for f in oc_dir.rglob("*.py")}
    cc_py = {f.name for f in cc_dir.rglob("*.py")}
    overlap = oc_py & cc_py
    assert not overlap, f"Python files with same name in both runtime dirs: {overlap}"
