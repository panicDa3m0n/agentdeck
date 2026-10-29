"""Test della richiesta web monouso per i segreti del proprietario (O23.T1): server vero su 127.0.0.1, schermata.

Si lanciano dalla cartella deck/: python3 -m unittest discover -s tests
Codice: agentdeck/secret_drop.py, agentdeck/components/secret.py. Documentazione: docs/segreti.md.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["AGENTDECK_NO_LOG"] = "1"

from agentdeck import cli  # noqa: E402
from agentdeck import secret_drop as sd  # noqa: E402
from agentdeck.components.home import Home  # noqa: E402
from agentdeck.components.secret import SERVER, Secret  # noqa: E402
from agentdeck.engine import Deck  # noqa: E402
from agentdeck.protocol import instruction_texts, validate  # noqa: E402

KEY = "sk-api-" + "Ab3" * 20
TG_TOKEN = "123456789:" + "AAbbCCdd_-" * 4


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(root / "config"),
                                                "XDG_STATE_HOME": str(root / "state")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class ValuesTests(Base):
    def test_minimax_key(self):
        self.assertEqual(sd.content_for("minimax", {"key": ["  " + KEY + "\n"]}), KEY + "\n")
        for bad in ("", "corta", "con uno spazio dentro la chiave lunga", "x" * 600):
            with self.assertRaises(sd.Refused):
                sd.content_for("minimax", {"key": [bad]})

    def test_telegram_keeps_other_settings(self):
        path = sd.slot_path("telegram")
        sd.write_secret(path, json.dumps({"token": "vecchio", "chat_id": 1, "poll_s": 30}))
        content = json.loads(sd.content_for("telegram", {"token": [TG_TOKEN], "chat_id": ["-100123"]}))
        self.assertEqual(content, {"token": TG_TOKEN, "chat_id": -100123, "poll_s": 30})
        with self.assertRaises(sd.Refused):
            sd.content_for("telegram", {"token": ["123:abc"], "chat_id": ["1"]})
        with self.assertRaises(sd.Refused):
            sd.content_for("telegram", {"token": [TG_TOKEN], "chat_id": ["io"]})

    def test_write_secret_and_presence(self):
        path = sd.slot_path("minimax")
        sd.write_secret(path, KEY + "\n")
        self.assertEqual(path.read_text(), KEY + "\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        info = sd.presence("minimax")
        self.assertEqual((info["present"], info["mode"], info["bytes"]), (True, "0o600", len(KEY) + 1))
        self.assertNotIn(KEY, json.dumps(info))
        self.assertFalse(sd.presence("telegram")["present"])
        self.assertEqual([p.name for p in path.parent.iterdir()], ["minimax.key"])  # nessun file temporaneo

    def test_lan_address_only_private(self):
        def fake(src):
            return lambda *a, **k: subprocess.CompletedProcess(a, 0, json.dumps([{"prefsrc": src}]), "")
        self.assertEqual(sd.lan_address(fake("192.168.1.49")), "192.168.1.49")
        self.assertIsNone(sd.lan_address(fake("93.184.216.34")))
        self.assertIsNone(sd.lan_address(fake("127.0.0.1")))
        self.assertIsNone(sd.lan_address(lambda *a, **k: subprocess.CompletedProcess(a, 2, "", "err")))


class ServerTests(Base):
    """Il server monouso, vero, su 127.0.0.1 e una porta libera."""

    def start(self, name="minimax", ttl=30):
        req = sd.new_request(name, "127.0.0.1", port=0, ttl_s=ttl)
        self.assertEqual(sd.request_file().stat().st_mode & 0o777, 0o600)
        drop = sd.Drop(req)
        self.base = f"http://127.0.0.1:{drop.port}"
        self.url = f"{self.base}/{req['token']}"
        self.result = {}
        self.thread = threading.Thread(target=lambda: self.result.update(outcome=drop.run()))
        self.thread.start()
        return req

    def finish(self):
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        return self.result["outcome"]

    def call(self, url, form=None):
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        try:
            with urllib.request.urlopen(url, data=data, timeout=5) as r:
                return r.status, dict(r.headers), r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, dict(e.headers), e.read().decode()

    def test_one_valid_value_then_closed(self):
        self.start()
        self.assertEqual(self.call(self.base + "/")[0], 404)
        self.assertEqual(self.call(self.base + "/sbagliato")[0], 404)
        code, headers, page = self.call(self.url)
        self.assertEqual(code, 200)
        self.assertIn('name="key"', page)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.call(self.url, {"key": "corta"})[0], 400)
        code, _, page = self.call(self.url, {"key": KEY})
        self.assertEqual((code, "Ricevuto" in page), (200, True))
        self.assertEqual(self.finish(), "received")
        self.assertEqual(sd.slot_path("minimax").read_text(), KEY + "\n")
        self.assertIsNone(sd.load_request())
        log = sd.log_file().read_text()
        self.assertNotIn(KEY, log)
        self.assertEqual(sd.history()[0]["outcome"], "received")
        self.assertEqual(sd.history()[0]["from"], "127.0.0.1")
        with self.assertRaises(OSError):  # il server non c'è più
            urllib.request.urlopen(self.url, timeout=2)

    def test_telegram_form(self):
        self.start("telegram")
        self.assertIn('name="chat_id"', self.call(self.url)[2])
        self.assertEqual(self.call(self.url, {"token": TG_TOKEN, "chat_id": "42"})[0], 200)
        self.assertEqual(self.finish(), "received")
        self.assertEqual(json.loads(sd.slot_path("telegram").read_text()), {"token": TG_TOKEN, "chat_id": 42})

    def test_too_many_bad_values(self):
        self.start()
        for _ in range(sd.MAX_BAD):
            self.assertEqual(self.call(self.url, {"key": "no"})[0], 400)
        self.assertEqual(self.finish(), "too_many_attempts")
        self.assertFalse(sd.slot_path("minimax").exists())

    def test_too_many_wrong_addresses(self):
        with mock.patch.object(sd, "MAX_STRAY", 3):
            self.start()
            for i in range(3):
                self.assertEqual(self.call(f"{self.base}/prova{i}")[0], 404)
            self.assertEqual(self.finish(), "too_many_attempts")

    def test_expiry(self):
        self.start(ttl=1)
        self.assertEqual(self.finish(), "expired")
        self.assertEqual(sd.history()[0], {"time": sd.history()[0]["time"], "name": "minimax", "outcome": "expired"})

    def test_serve_entry_point(self):
        self.assertEqual(sd.serve(), 1)  # nessuna richiesta
        req = sd.new_request("minimax", "127.0.0.1", ttl_s=-1)
        self.assertEqual(sd.serve(), 0)
        self.assertIsNone(sd.load_request())
        self.assertEqual(sd.history()[0]["outcome"], "expired")
        self.assertTrue(req["token"])


class FakeSystemd:
    """systemctl e systemd-run finti: l'unità risulta attiva dopo l'avvio, se start_ok."""

    def __init__(self, start_ok=True):
        self.calls, self.active, self.start_ok = [], False, start_ok

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        out = ""
        if "systemd-run" in argv:
            self.active = self.start_ok
            return subprocess.CompletedProcess(argv, 0 if self.start_ok else 1, "", "" if self.start_ok else "boom")
        if argv[-2:] == ["stop", sd.UNIT]:
            self.active = False
        if "is-active" in argv:
            out = "active\n" if self.active else "inactive\n"
        return subprocess.CompletedProcess(argv, 0, out, "")


class ScreenTests(Base):
    def deck(self, fake, lan="192.168.1.49"):
        return Deck([Home(), Secret(sh=fake, lan=lambda: lan, wait_s=0.5)])

    def call(self, deck, *argv):
        result, code = cli.render(deck, list(argv))
        as_json = json.loads(json.dumps(result))
        self.assertEqual(validate(as_json), [], argv)
        req = sd.load_request()
        for text in instruction_texts(as_json):
            self.assertNotIn(KEY, text)
            if req:
                self.assertNotIn(req["token"], text, "the token reached the instruction channel")
        return as_json, code

    def test_view_request_and_cancel(self):
        fake = FakeSystemd()
        deck = self.deck(fake)
        view, _ = self.call(deck, "/secret")
        self.assertEqual([s["name"] for s in view["data"]["slots"]], ["minimax", "telegram"])
        self.assertIsNone(view["data"]["request"])
        done, code = self.call(deck, "/secret", "request", "name=minimax")
        self.assertEqual((done["status"], code), ("done", 0))
        req = sd.load_request()
        self.assertEqual(done["data"]["request"]["url"], f"http://192.168.1.49:{sd.PORT}/{req['token']}")
        self.assertGreaterEqual(len(req["token"]), 32)
        run = next(c for c in fake.calls if "systemd-run" in c)
        self.assertIn(f"--unit={sd.UNIT}", run)
        self.assertIn(f"--property=RuntimeMaxSec={sd.TTL_S + 60}", run)
        self.assertEqual(run[-1], str(SERVER))
        self.assertFalse(any(req["token"] in a for c in fake.calls for a in c), "the token is in a command line")
        again, _ = self.call(deck, "/secret")
        self.assertEqual((again["data"]["request"]["name"], again["data"]["request"]["server_running"]),
                         ("minimax", True))
        cancelled, _ = self.call(deck, "/secret", "cancel")
        self.assertEqual(cancelled["data"]["cancelled"], "minimax")
        self.assertIsNone(sd.load_request())
        self.assertEqual(sd.history()[0]["outcome"], "cancelled")
        self.assertIn(["sudo", "-n", "systemctl", "stop", sd.UNIT], fake.calls)

    def test_no_home_network(self):
        result, code = self.call(self.deck(FakeSystemd(), lan=None), "/secret", "request", "name=telegram")
        self.assertEqual((result["error"]["code"], code), ("NOT_AVAILABLE", 1))
        self.assertIsNone(sd.load_request())

    def test_server_that_does_not_start(self):
        result, _ = self.call(self.deck(FakeSystemd(start_ok=False)), "/secret", "request", "name=minimax")
        self.assertEqual(result["error"]["code"], "FAILED")
        self.assertIsNone(sd.load_request())
        self.assertEqual(sd.history()[0]["outcome"], "not_started")

    def test_bad_name(self):
        result, _ = self.call(self.deck(FakeSystemd()), "/secret", "request", "name=ssh")
        self.assertEqual(result["error"]["code"], "BAD_PARAM")


if __name__ == "__main__":
    unittest.main()
