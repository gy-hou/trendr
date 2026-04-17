"""Contract tests for claude-code sibling files (skills, agents, commands)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
AGENTS_DIR = REPO / "agents"
COMMANDS_DIR = REPO / "runtimes" / "claude-code" / "commands"

ALLOWED_TOOLS = frozenset(
    [
        "WebFetch",
        "WebSearch",
        "Bash",
        "Read",
        "Write",
        "Grep",
        "Glob",
        "Agent",
        "Edit",
        "Skill",
        "NotebookEdit",
        "mcp__ide__executeCode",
        "mcp__ide__getDiagnostics",
    ]
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _skill_sibling_files():
    return sorted(SKILLS_DIR.glob("*/claude-code.md"))


def _agent_sibling_files():
    return sorted(AGENTS_DIR.glob("*/claude-code.md"))


def _command_files():
    return sorted(COMMANDS_DIR.rglob("*.md"))


# ---------------------------------------------------------------------------
# SKILL.md: Runtime Router
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_md", sorted(SKILLS_DIR.glob("*/SKILL.md")), ids=lambda p: p.parent.name)
def test_skill_md_has_runtime_router(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    assert "Runtime Router" in text, f"{skill_md} missing Runtime Router section"
    assert "claude-code.md" in text, f"{skill_md} Runtime Router doesn't reference ./claude-code.md"


# ---------------------------------------------------------------------------
# skills/*/claude-code.md frontmatter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cc_md", _skill_sibling_files(), ids=lambda p: p.parent.name)
def test_skill_claude_code_frontmatter_required_fields(cc_md):
    fm = _parse_frontmatter(cc_md.read_text(encoding="utf-8"))
    assert fm.get("runtime") == "claude-code", f"{cc_md}: expected runtime: claude-code"
    assert fm.get("parent_skill"), f"{cc_md}: missing parent_skill"
    assert "allowed-tools" in fm, f"{cc_md}: missing allowed-tools"


@pytest.mark.parametrize("cc_md", _skill_sibling_files(), ids=lambda p: p.parent.name)
def test_skill_claude_code_allowed_tools_valid(cc_md):
    fm = _parse_frontmatter(cc_md.read_text(encoding="utf-8"))
    tools = fm.get("allowed-tools", [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",")]
    unknown = [t for t in tools if t not in ALLOWED_TOOLS]
    assert not unknown, f"{cc_md}: unknown tools {unknown}"


# ---------------------------------------------------------------------------
# agents/*/claude-code.md frontmatter
# ---------------------------------------------------------------------------

AGENT_REQUIRED = {"name", "description", "tools", "model", "runtime", "parent_agent"}


@pytest.mark.parametrize("agent_md", _agent_sibling_files(), ids=lambda p: p.parent.name)
def test_agent_claude_code_frontmatter_required_fields(agent_md):
    fm = _parse_frontmatter(agent_md.read_text(encoding="utf-8"))
    missing = AGENT_REQUIRED - set(fm.keys())
    assert not missing, f"{agent_md}: missing fields {missing}"
    assert fm.get("runtime") == "claude-code", f"{agent_md}: expected runtime: claude-code"


@pytest.mark.parametrize("agent_md", _agent_sibling_files(), ids=lambda p: p.parent.name)
def test_agent_tools_subset_of_allowed(agent_md):
    fm = _parse_frontmatter(agent_md.read_text(encoding="utf-8"))
    tools_raw = fm.get("tools", "")
    if isinstance(tools_raw, list):
        tools = tools_raw
    else:
        tools = [t.strip() for t in str(tools_raw).split(",")]
    unknown = [t for t in tools if t and t not in ALLOWED_TOOLS]
    assert not unknown, f"{agent_md}: unknown tools {unknown}"


# ---------------------------------------------------------------------------
# runtimes/claude-code/commands/**/*.md
# ---------------------------------------------------------------------------

COMMAND_REQUIRED = {"description", "argument-hint", "allowed-tools"}


@pytest.mark.parametrize("cmd_md", _command_files(), ids=lambda p: p.relative_to(COMMANDS_DIR).as_posix())
def test_command_frontmatter_required_fields(cmd_md):
    fm = _parse_frontmatter(cmd_md.read_text(encoding="utf-8"))
    missing = COMMAND_REQUIRED - set(fm.keys())
    assert not missing, f"{cmd_md}: missing fields {missing}"


@pytest.mark.parametrize("cmd_md", _command_files(), ids=lambda p: p.relative_to(COMMANDS_DIR).as_posix())
def test_command_body_has_arguments_variable(cmd_md):
    text = cmd_md.read_text(encoding="utf-8")
    # Strip frontmatter before checking body
    body = _FRONTMATTER_RE.sub("", text, count=1)
    has_args = "$ARGUMENTS" in body or "$1" in body
    assert has_args, f"{cmd_md}: body lacks $ARGUMENTS or $1"


@pytest.mark.parametrize(
    "cmd_md",
    [p for p in _command_files() if p.name != "tr.md"],
    ids=lambda p: p.relative_to(COMMANDS_DIR).as_posix(),
)
def test_subcommand_body_has_repo_root(cmd_md):
    text = cmd_md.read_text(encoding="utf-8")
    assert "{{repo_root}}" in text or "repo_root" in text, f"{cmd_md}: missing {{repo_root}} placeholder"
