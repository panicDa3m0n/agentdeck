"""Test delle skill di AgentDeck per Claude Code (O10.T9): intestazione valida, nomi coerenti, file di supporto
presenti, e ogni strumento MCP citato esiste davvero tra quelli che deck mcp offre.

Si lanciano dalla cartella deck/: python3 -m unittest discover -s tests
Codice: claude/skills/. Documentazione: docs/claude-code.md, "Le skill".
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent / "claude" / "skills"
sys.path.insert(0, str(HERE.parent))
os.environ["AGENTDECK_NO_LOG"] = "1"

from agentdeck import mcp  # noqa: E402


def front_matter(text: str) -> dict:
    head = text.split("---")[1]
    fields = {}
    for line in head.strip().splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


class SkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = tempfile.TemporaryDirectory()
        os.environ["XDG_STATE_HOME"] = cls.state.name
        cls.tools = {"mcp__deck__" + t["name"] for t in mcp.Server().tools()}

    @classmethod
    def tearDownClass(cls):
        cls.state.cleanup()

    def skills(self):
        return sorted(d for d in SKILLS.iterdir() if d.is_dir())

    def test_there_are_skills_for_the_gate(self):
        names = {d.name for d in self.skills()}
        for needed in ("agentdeck-install-package", "agentdeck-change-service", "agentdeck-interactive-program",
                       "agentdeck-alerts-and-obligations", "agentdeck-rollback"):
            self.assertIn(needed, names)

    def test_front_matter(self):
        for d in self.skills():
            text = (d / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), d.name)
            fields = front_matter(text)
            self.assertEqual(fields.get("name"), d.name)
            self.assertTrue(d.name.startswith("agentdeck-"))
            self.assertTrue(20 < len(fields.get("description", "")) <= 1536, d.name)
            self.assertLess(len(text.splitlines()), 500, d.name)

    def test_mentioned_tools_exist(self):
        for d in self.skills():
            for f in d.glob("*.md"):
                for tool in set(re.findall(r"mcp__deck__[a-z0-9_]+", f.read_text())):
                    self.assertIn(tool, self.tools, f"{f.relative_to(SKILLS)} mentions {tool}")

    def test_links_and_skill_names_resolve(self):
        names = {d.name for d in self.skills()}
        for d in self.skills():
            for f in d.glob("*.md"):
                text = f.read_text()
                for link in re.findall(r"\]\(([^)]+\.md)\)", text):
                    self.assertTrue((d / link).is_file(), f"{f.name} links {link}")
                for other in re.findall(r"skill (agentdeck-[a-z-]+)", text):
                    self.assertIn(other, names, f"{f.name} names {other}")


if __name__ == "__main__":
    unittest.main()
