"""Tests for runtimes/claude-code/plugin.json — authority source validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO / "runtimes" / "claude-code" / "plugin.json"
MANIFEST_DIR = MANIFEST_PATH.parent


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Required top-level fields
# ---------------------------------------------------------------------------


def test_manifest_required_fields(manifest):
    for field in ("name", "version", "description"):
        assert field in manifest, f"plugin.json missing required field: {field}"


def test_manifest_name(manifest):
    assert manifest["name"] == "trendr"


def test_manifest_version_format(manifest):
    parts = manifest["version"].split(".")
    assert len(parts) == 3, "version must be semver (X.Y.Z)"
    assert all(p.isdigit() for p in parts), "version parts must be digits"


# ---------------------------------------------------------------------------
# Agent paths resolve to real files
# ---------------------------------------------------------------------------


def test_manifest_agents_exist(manifest):
    for rel_path in manifest.get("agents", []):
        resolved = (MANIFEST_DIR / rel_path).resolve()
        assert resolved.exists(), f"agent path not found: {rel_path} → {resolved}"


# ---------------------------------------------------------------------------
# Command paths resolve to real files
# ---------------------------------------------------------------------------


def test_manifest_commands_exist(manifest):
    for rel_path in manifest.get("commands", []):
        resolved = (MANIFEST_DIR / rel_path).resolve()
        assert resolved.exists(), f"command path not found: {rel_path} → {resolved}"


# ---------------------------------------------------------------------------
# Skill directories resolve to real directories
# ---------------------------------------------------------------------------


def test_manifest_skills_exist(manifest):
    for rel_path in manifest.get("skills", []):
        resolved = (MANIFEST_DIR / rel_path).resolve()
        assert resolved.exists(), f"skill path not found: {rel_path} → {resolved}"
        assert resolved.is_dir(), f"skill path is not a directory: {resolved}"


# ---------------------------------------------------------------------------
# Hooks reference real scripts
# ---------------------------------------------------------------------------


def test_manifest_hook_scripts_exist(manifest):
    hooks_section = manifest.get("hooks", {})
    for event, hook_list in hooks_section.items():
        for group in hook_list:
            for hook_def in group.get("hooks", []):
                cmd = hook_def.get("command", "")
                # Extract path from command string (quoted path after `python `)
                for token in cmd.split():
                    cleaned = token.strip('"').strip("'")
                    if cleaned.endswith(".py"):
                        # Replace env variable with literal hooks dir
                        script_rel = cleaned.replace("${CLAUDE_PLUGIN_ROOT}", str(MANIFEST_DIR))
                        script_path = Path(script_rel)
                        assert script_path.exists(), (
                            f"hook script not found for {event}: {script_path}"
                        )


# ---------------------------------------------------------------------------
# .claude-plugin/plugin.json consistency (if it exists)
# ---------------------------------------------------------------------------


def test_symlink_or_content_matches_authority(manifest):
    symlink_target = REPO / ".claude-plugin" / "plugin.json"
    if not symlink_target.exists() and not symlink_target.is_symlink():
        pytest.skip(".claude-plugin/plugin.json not installed yet")

    if symlink_target.is_symlink():
        link_dest = symlink_target.resolve()
        assert link_dest == MANIFEST_PATH.resolve(), (
            f".claude-plugin/plugin.json symlink points to {link_dest}, expected {MANIFEST_PATH}"
        )
    else:
        installed = json.loads(symlink_target.read_text(encoding="utf-8"))
        assert installed == manifest, ".claude-plugin/plugin.json content differs from authority source"
