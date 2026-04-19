import unittest
from pathlib import Path


class SkillContractsTestCase(unittest.TestCase):
    REPO_ROOT = Path(__file__).resolve().parents[1]
    CORE_SKILLS = [
        "paper-scout",
        "paper-analyzer",
        "review-writer",
        "verifier",
        "trendr-watchdog",
        "platform-hotspots",
        "chrome-cdp-setup",
        "research-vault",
    ]

    def test_core_skills_have_runtime_router_and_dormant_semantics(self) -> None:
        for skill in self.CORE_SKILLS:
            with self.subTest(skill=skill):
                path = self.REPO_ROOT / "skills" / skill / "SKILL.md"
                text = path.read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertIn("runtime router", lowered)
                # "休眠" is the Chinese equivalent of "dormant" used in the updated Runtime Router format
                has_dormant_semantics = "dormant" in lowered or "休眠" in text
                self.assertTrue(
                    has_dormant_semantics,
                    f"SKILL.md for '{skill}' must contain dormancy semantics ('dormant' or '休眠')",
                )

    def test_core_skills_have_runtime_siblings(self) -> None:
        for skill in self.CORE_SKILLS:
            with self.subTest(skill=skill):
                cc_sibling = self.REPO_ROOT / "skills" / skill / "claude-code.md"
                codex_sibling = self.REPO_ROOT / "skills" / skill / "codex.md"
                self.assertTrue(cc_sibling.exists(), f"Missing claude-code.md sibling for skill '{skill}'")
                self.assertTrue(codex_sibling.exists(), f"Missing codex.md sibling for skill '{skill}'")

    def test_claude_code_sibling_has_valid_frontmatter(self) -> None:
        required_keys = {"runtime", "parent_skill", "allowed-tools"}
        for skill in self.CORE_SKILLS:
            with self.subTest(skill=skill):
                path = self.REPO_ROOT / "skills" / skill / "claude-code.md"
                text = path.read_text(encoding="utf-8")
                parts = text.split("---", 2)
                self.assertGreaterEqual(len(parts), 3, f"No valid frontmatter in {path}")
                fm_text = parts[1]
                for key in required_keys:
                    self.assertIn(key, fm_text, f"Missing '{key}' in frontmatter of {path}")

    def test_codex_sibling_has_valid_frontmatter(self) -> None:
        required_keys = {"runtime", "parent_skill", "allowed-tools"}
        for skill in self.CORE_SKILLS:
            with self.subTest(skill=skill):
                path = self.REPO_ROOT / "skills" / skill / "codex.md"
                text = path.read_text(encoding="utf-8")
                parts = text.split("---", 2)
                self.assertGreaterEqual(len(parts), 3, f"No valid frontmatter in {path}")
                fm_text = parts[1]
                for key in required_keys:
                    self.assertIn(key, fm_text, f"Missing '{key}' in frontmatter of {path}")


if __name__ == "__main__":
    unittest.main()
