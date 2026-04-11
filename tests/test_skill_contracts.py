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
                self.assertIn("dormant", lowered)


if __name__ == "__main__":
    unittest.main()
