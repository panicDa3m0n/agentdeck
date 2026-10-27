"""Test del server della pagina dello schermo (O15.T3): codice obbligatorio, host locale, solo le schermate
ammesse, azioni con anteprima e conferma, luce dello schermo, e una pagina che non carica nulla da fuori e non
mette testo esterno nell'HTML.

Il server gira davvero su 127.0.0.1, su una porta libera; le sessioni Claude sono quelle finte di
test_claude_sessions. Si lanciano dalla cartella deck/: python3 -m unittest discover -s tests
Codice: agentdeck/ui.py, ui/index.html. Documentazione: docs/interfacce.md.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
os.environ["AGENTDECK_NO_LOG"] = "1"

from agentdeck import ui  # noqa: E402
from agentdeck.components.claude import Claude  # noqa: E402
from agentdeck.components.home import Home  # noqa: E402
from agentdeck.engine import Deck  # noqa: E402
from test_claude_sessions import INJECTION, FakeDeck  # noqa: E402

TOKEN = "0123456789abcdef0123456789abcdef"


class ArgvTests(unittest.TestCase):
    def test_allowed(self):
        self.assertEqual(ui.action_argv({"path": "/claude", "action": "close", "params": {"id": "2954621b"}}),
                         ["/claude", "close", "id=2954621b"])

    def test_refused(self):
        for body in ({"path": "/service", "action": "stop", "params": {"name": "sshd"}},
                     {"path": "/claude", "action": "Close"},
                     {"path": "/claude", "action": "open", "params": {"name": 3}},
                     {"path": "/claude", "action": "open", "params": {"Bad": "x"}},
                     {"path": "/claude", "action": "open", "params": {"name": "a\nb"}},
                     {"path": "/claude", "action": "open", "params": {"name": "x" * 201}},
                     {"path": "/claude", "action": "open", "params": ["name=x"]}):
            self.assertIsNone(ui.action_argv(body), body)


class BacklightTests(unittest.TestCase):
    def test_levels(self):
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / "amdgpu_bl1"
            dev.mkdir()
            (dev / "max_brightness").write_text("65535\n")
            calls = []
            run = lambda argv, **kw: calls.append((argv, kw["input"])) or subprocess.CompletedProcess(argv, 0)
            self.assertEqual(ui.backlight("dim", Path(tmp), run), 5242)
            self.assertEqual(ui.backlight("full", Path(tmp), run), 65535)
            self.assertIsNone(ui.backlight("blink", Path(tmp), run))
            self.assertEqual(calls[0], (["sudo", "-n", "tee", str(dev / "brightness")], "5242\n"))


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, "state")
        fake = FakeDeck(Path(self.tmp.name))
        self.fake = fake
        self.light = []

        class Handler(ui.Handler):
            token = TOKEN
            deck_factory = staticmethod(lambda: Deck([Home(), Claude(fake.sessions())]))
            set_backlight = staticmethod(lambda level: self.light.append(level) or 1)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def request(self, path, body=None, *, token=TOKEN, host=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method="POST" if body else "GET",
                                     data=json.dumps(body).encode() if body else None)
        if token:
            req.add_header("X-Deck-Token", token)
        if host:
            req.add_header("Host", host)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.headers, e.read()

    def screen(self, path, body=None):
        code, _, raw = self.request(path, body)
        self.assertEqual(code, 200, raw)
        return json.loads(raw)

    def test_page_is_served_with_a_strict_policy(self):
        code, headers, raw = self.request("/", token=None)
        self.assertEqual(code, 200)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertIn(b"Sessioni Claude", raw)

    def test_api_needs_the_token_and_a_local_host(self):
        self.assertEqual(self.request("/api/home", token=None)[0], 401)
        self.assertEqual(self.request("/api/home", token="x" * 32)[0], 401)
        self.assertEqual(self.request("/api/home", host="evil.example:80")[0], 403)
        self.assertEqual(self.request("/api/screen?path=/status")[0], 404)
        self.assertEqual(self.request("/api/action", {"path": "/service", "action": "stop"})[0], 400)

    def test_home_and_sessions(self):
        home = self.screen("/api/home")
        self.assertEqual(home["sessions"], {"total": 2, "busy": 1, "idle": 1})
        s = self.screen("/api/screen?path=/claude")
        self.assertIn(INJECTION, [x["title"] for x in s["data"]["sessions"]])

    def test_open_and_close_go_through_deck(self):
        opened = self.screen("/api/action", {"path": "/claude", "action": "open", "params": {"name": "sessione-2310"}})
        self.assertEqual(opened["status"], "done")
        sid = opened["data"]["session"]["id"]
        preview = self.screen("/api/action", {"path": "/claude", "action": "close", "params": {"id": sid}})
        self.assertEqual(preview["status"], "confirm")
        done = self.screen("/api/action", {"path": "/claude", "action": "close",
                                           "params": {"id": sid, "confirm": preview["confirm"]["token"]}})
        self.assertEqual((done["status"], done["data"]["signal"]), ("done", "SIGINT"))

    def test_backlight(self):
        self.assertEqual(self.screen("/api/backlight", {"level": "dim"})["value"], 1)
        self.assertEqual(self.light, ["dim"])


class PageTests(unittest.TestCase):
    def test_nothing_from_outside_and_no_html_from_data(self):
        page = (HERE.parent / "ui" / "index.html").read_text()
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("insertAdjacentHTML", page)
        self.assertEqual(re.findall(r"(?:src|href)=\"https?://", page), [])
        self.assertNotIn("@import", page)


if __name__ == "__main__":
    unittest.main()
