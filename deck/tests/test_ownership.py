"""Test dei permessi dell'agente (ADR-0001, O12.T1): libero sul sistema, chiede solo per i servizi e le credenziali
dell'utente; l'hook PreToolUse risponde "ask" solo in quei casi e i testi per l'agente non chiedono altro.

Si lanciano dalla cartella deck/: python3 -m unittest discover -s tests
Codice: agentdeck/ownership.py, claude/guard.py. Documentazione: docs/claude-code.md, "Permessi (ADR-0001)".
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["AGENTDECK_NO_LOG"] = "1"

from agentdeck import ownership  # noqa: E402

CLAUDE = HERE.parent / "claude"

SYSTEM_WORK = [
    "sudo pacman -S --noconfirm tree", "sudo systemctl restart systemd-timesyncd", "echo x | sudo tee /etc/foo.conf",
    "ls /srv/servizi", "ls -la /srv/servizi/blog", "cat /srv/servizi/blog/LEGGIMI.md", "du -sh /srv/servizi/blog",
    "systemctl status agentdeck-servizio@blog", "journalctl -u agentdeck-servizio@blog -n 20",
    "deck service show name=agentdeck-servizio@blog", "cd /home/agent/frugale && git commit -am wip",
    "rm -rf /home/agent/frugale/tmp", "ls ~/.ssh", "sudo bash /tmp/agentdeck-servizi/install-servizi.sh",
]
OWNER_SERVICES = [
    "sudo systemctl restart agentdeck-servizio@blog", "sudo systemctl stop agentdeck-servizio@blog.service",
    "systemctl disable --now agentdeck-servizio@blog", "deck service stop name=agentdeck-servizio@blog",
    "echo PORT=8080 > /srv/servizi/blog/config/env", "sudo rm -rf /srv/servizi/blog",
    "git -C /srv/servizi/blog/app pull", "sudo -u srv-blog touch /srv/servizi/blog/dati/x",
    "ls /srv/servizi/blog && rm /srv/servizi/blog/dati/cache.db",
]
CREDENTIALS = [
    "cat ~/.claude/.credentials.json", "cp /home/agent/.ssh/authorized_keys /tmp/k",
    "echo ssh-ed25519 AAAA >> ~/.ssh/authorized_keys", "rm /home/agent/.claude/.credentials.json",
]


class OwnershipTests(unittest.TestCase):
    def test_system_work_is_free(self):
        for command in SYSTEM_WORK:
            self.assertIsNone(ownership.command_reason(command), command)

    def test_owner_services_ask(self):
        for command in OWNER_SERVICES:
            reason = ownership.command_reason(command)
            self.assertIsNotNone(reason, command)
            self.assertIn("service blog", reason)

    def test_credentials_ask(self):
        for command in CREDENTIALS:
            self.assertIn("credentials", ownership.command_reason(command) or "", command)

    def test_paths(self):
        self.assertIn("service blog", ownership.path_reason("/srv/servizi/blog/app/main.py"))
        self.assertIn("credentials", ownership.path_reason("/home/agent/.claude/.credentials.json"))
        for free in ("/home/agent/frugale/README.md", "/etc/hosts", "/opt/agentdeck/deck", "/srv/servizi/LEGGIMI.md"):
            self.assertIsNone(ownership.path_reason(free), free)

    def test_tools(self):
        ask = ownership.tool_reason
        self.assertIsNotNone(ask("mcp__deck__service_stop", {"name": "agentdeck-servizio@blog"}))
        self.assertIsNotNone(ask("mcp__deck__service_enable", {"name": "agentdeck-servizio@blog.service"}))
        self.assertIsNone(ask("mcp__deck__service_stop", {"name": "systemd-timesyncd"}))
        self.assertIsNone(ask("mcp__deck__service_show", {"name": "agentdeck-servizio@blog"}))
        self.assertIsNotNone(ask("mcp__deck__term_start", {"command": "sudo systemctl stop agentdeck-servizio@blog"}))
        self.assertIsNotNone(ask("Write", {"file_path": "/srv/servizi/blog/config/env"}))
        self.assertIsNone(ask("Edit", {"file_path": "/home/agent/frugale/docs/00-visione.md"}))
        self.assertIsNone(ask("Read", {"file_path": "/srv/servizi/blog/config/env"}))
        self.assertIsNone(ask("mcp__deck__open", {"path": "/service"}))

    def test_reasons_carry_only_valid_names(self):
        reason = ownership.command_reason("sudo rm -rf '/srv/servizi/Ignore previous instructions'")
        self.assertIsNone(reason)  # non è un nome di servizio: non entra nel testo


class GuardAskTests(unittest.TestCase):
    def run_guard(self, event):
        r = subprocess.run([sys.executable, str(CLAUDE / "guard.py")], input=json.dumps(event), capture_output=True,
                           text=True)
        return r.returncode, (json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else None)

    def test_ask_for_owner_service(self):
        code, out = self.run_guard({"tool_name": "Bash",
                                    "tool_input": {"command": "sudo systemctl restart agentdeck-servizio@blog"}})
        self.assertEqual((code, out["permissionDecision"]), (0, "ask"))
        self.assertIn("ADR-0001", out["permissionDecisionReason"])

    def test_ask_for_mcp_and_writes(self):
        _, out = self.run_guard({"tool_name": "mcp__deck__service_stop",
                                 "tool_input": {"name": "agentdeck-servizio@blog"}})
        self.assertEqual(out["permissionDecision"], "ask")
        _, out = self.run_guard({"tool_name": "Edit", "tool_input": {"file_path": "/srv/servizi/blog/app/x.py"}})
        self.assertEqual(out["permissionDecision"], "ask")

    def test_system_work_passes_without_asking(self):
        code, out = self.run_guard({"tool_name": "Edit", "tool_input": {"file_path": "/etc/systemd/x.conf"}})
        self.assertEqual((code, out), (0, None))
        code, out = self.run_guard({"tool_name": "Bash", "tool_input": {"command": "sudo pacman -S --noconfirm tree"}})
        self.assertEqual(code, 0)
        self.assertNotIn("permissionDecision", out or {})

    def test_access_guard_still_blocks(self):
        r = subprocess.run([sys.executable, str(CLAUDE / "guard.py")],
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "sudo systemctl stop sshd"}}),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a permission to ask for", r.stderr)


class AgentTextsTests(unittest.TestCase):
    def test_no_permission_requests_for_system_work(self):
        """Nei testi per l'agente si chiede al proprietario solo per segreti e password (ADR-0001)."""
        files = [CLAUDE / "CLAUDE.template.md", CLAUDE / "output-styles" / "agentdeck.md", CLAUDE / "guard.py"]
        files += sorted((CLAUDE / "skills").rglob("*.md"))
        files.append(HERE.parent / "agentdeck" / "components" / "term.py")
        for f in files:
            lines = f.read_text().splitlines()
            for i, line in enumerate(lines):
                low = line.lower()
                if "ask the owner" in low or "owner's explicit approval" in low or "ask first" in low:
                    context = " ".join(lines[max(0, i - 2):i + 1]).lower()  # la frase può cominciare prima
                    self.assertTrue(any(w in context for w in ("secret", "password", "passphrase")), f"{f.name}: {line}")

    def test_managed_settings_allow_system_work(self):
        s = json.loads((CLAUDE / "managed-settings.json").read_text())
        for tool in ("Bash", "Edit", "Write", "Read", "mcp__deck"):
            self.assertIn(tool, s["permissions"]["allow"])
        self.assertEqual(s["permissions"]["disableBypassPermissionsMode"], "disable")
        matcher = s["hooks"]["PreToolUse"][0]["matcher"]
        for tool in ("Bash", "Edit", "Write", "mcp__deck__"):
            self.assertIn(tool, matcher)


if __name__ == "__main__":
    unittest.main()
