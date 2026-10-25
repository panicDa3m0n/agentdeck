"""Test dello schermo della Deck: pulizia del testo, segreti oscurati, comandi ed esiti di deck.

Si lanciano dalla cartella deck/: python3 -m unittest discover -s tests
Documentazione: docs/schermo.md.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "screen"))
os.environ["AGENTDECK_NO_LOG"] = "1"

import agentdeck_screen as screen  # noqa: E402
from agentdeck import cli  # noqa: E402
from agentdeck.components import all_components  # noqa: E402
from agentdeck.engine import Deck  # noqa: E402


def entry(ident, message):
    return {"SYSLOG_IDENTIFIER": ident, "MESSAGE": message, "__REALTIME_TIMESTAMP": "1792944000000000"}


class ScreenTests(unittest.TestCase):
    def test_control_sequences_are_removed(self):
        self.assertEqual(screen.clean("ls\x1b[2J\x07 -la"), "ls?[2J? -la")

    def test_secrets_are_hidden(self):
        hidden = screen.clean("curl -H Authorization: Bearer abc123")
        self.assertNotIn("abc123", hidden)
        self.assertEqual(hidden, "curl -H Authorization: *** ***")
        self.assertEqual(screen.clean("export API_KEY=sk-123 TOKEN=xyz"), "export API_KEY=*** TOKEN=***")
        self.assertEqual(screen.clean("login --password hunter2"), "login --password ***")

    def test_command_line(self):
        line = screen.format_entry(entry("agentdeck-cmd", "deck status"), 100)
        self.assertIn("agent@agentdeck", line)
        self.assertTrue(line.endswith("deck status"))

    def test_transfers_and_multiline(self):
        self.assertEqual(screen.describe_command("/usr/lib/ssh/sftp-server"), "(trasferimento di file)")
        self.assertEqual(screen.describe_command("rsync --server -logDtpre.iLsfxCIvu . /tmp/x"),
                         "(trasferimento di file)")
        self.assertEqual(screen.describe_command("for i in 1 2\ndo echo $i\ndone"), "for i in 1 2 …")

    def test_long_command_is_shortened(self):
        line = screen.format_entry(entry("agentdeck-cmd", "echo " + "x" * 300), 80)
        self.assertIn("…", line)

    def test_other_sources_are_ignored(self):
        self.assertIsNone(screen.format_entry(entry("sshd", "Accepted publickey"), 80))
        self.assertIsNone(screen.format_entry(entry("agentdeck", "not the deck format"), 80))

    def test_deck_summary_round_trip(self):
        deck = Deck(all_components())
        for argv, expected in ((["protocol"], "/protocol: ok"), (["/nowhere"], "/nowhere: errore NOT_FOUND")):
            result, _ = cli.render(deck, argv)
            color, text = screen.describe_deck(cli.call_summary(result, argv))
            self.assertEqual(text, expected)

    def test_deck_states(self):
        self.assertEqual(screen.describe_deck("/status||ok||3")[1], "/status: ok, 3 avvisi")
        self.assertEqual(screen.describe_deck("/snapshot|rollback|confirm||0")[1],
                         "/snapshot rollback: anteprima, in attesa di conferma")
        self.assertEqual(screen.describe_deck("/snapshot|create|done||0")[1], "/snapshot create: eseguito")


if __name__ == "__main__":
    unittest.main()
