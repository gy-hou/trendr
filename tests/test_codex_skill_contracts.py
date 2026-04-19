"""Contract tests for codex sibling files (skills and agents)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
AGENTS_DIR = REPO / "agents"

ALLOWED_TOOLS = frozenset(
    [
        "exec_command",
        "write_stdin",
        "read_thread_terminal",
        "apply_patch",
        "update_plan",
        "spawn_agent",
        "wait_agent",
        "send_input",
        "web",
        "view_image",
        "read_mcp_resource",
        "list_mcp_resources",
        "list_mcp_resource_templates",
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
    return sorted(SKILLS_DIR.glob("*/codex.md"))


def _agent_sibling_files():
    return sorted(AGENTS_DIR.glob("*/codex.md"))


@pytest.mark.parametrize("skill_md", sorted(SKILLS_DIR.glob("*/SKILL.md")), ids=lambda p: p.parent.name)
def test_skill_md_has_codex_runtime_router(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    assert "Runtime Router" in text, f"{skill_md} missing Runtime Router section"
    assert "codex.md" in text, f"{skill_md} Runtime Router doesn't reference ./codex.md"


@pytest.mark.parametrize("codex_md", _skill_sibling_files(), ids=lambda p: p.parent.name)
def test_skill_codex_frontmatter_required_fields(codex_md):
    fm = _parse_frontmatter(codex_md.read_text(encoding="utf-8"))
    assert fm.get("runtime") == "codex", f"{codex_md}: expected runtime: codex"
    assert fm.get("parent_skill"), f"{codex_md}: missing parent_skill"
    assert "allowed-tools" in fm, f"{codex_md}: missing allowed-tools"


@pytest.mark.parametrize("codex_md", _skill_sibling_files(), ids=lambda p: p.parent.name)
def test_skill_codex_allowed_tools_valid(codex_md):
    fm = _parse_frontmatter(codex_md.read_text(encoding="utf-8"))
    tools = fm.get("allowed-tools", [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",")]
    unknown = [t for t in tools if t not in ALLOWED_TOOLS]
    assert not unknown, f"{codex_md}: unknown tools {unknown}"


AGENT_REQUIRED = {"name", "description", "tools", "model", "runtime", "parent_agent"}


@pytest.mark.parametrize("agent_md", _agent_sibling_files(), ids=lambda p: p.parent.name)
def test_agent_codex_frontmatter_required_fields(agent_md):
    fm = _parse_frontmatter(agent_md.read_text(encoding="utf-8"))
    missing = AGENT_REQUIRED - set(fm.keys())
    assert not missing, f"{agent_md}: missing fields {missing}"
    assert fm.get("runtime") == "codex", f"{agent_md}: expected runtime: codex"


@pytest.mark.parametrize("agent_md", _agent_sibling_files(), ids=lambda p: p.parent.name)
def test_agent_codex_tools_subset_of_allowed(agent_md):
    fm = _parse_frontmatter(agent_md.read_text(encoding="utf-8"))
    tools_raw = fm.get("tools", "")
    if isinstance(tools_raw, list):
        tools = tools_raw
    else:
        tools = [t.strip() for t in str(tools_raw).split(",")]
    unknown = [t for t in tools if t and t not in ALLOWED_TOOLS]
    assert not unknown, f"{agent_md}: unknown tools {unknown}"
