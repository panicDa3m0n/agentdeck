"""Test dell'intermediario verso MiniMax (task O20.T1): adattamento delle richieste, chiave, streaming.

Il MiniMax finto è il server della prova degli agganci (agentdeck/claude_probe.FakeApi). Documentazione:
docs/agente-interno.md.
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentdeck import claude_probe  # noqa: E402
from agentdeck import minimax_proxy as mp  # noqa: E402

SYSTEM = [
    {"type": "text", "text": "x-anthropic-billing-header: cc_version=2.1.310.077; cc_entrypoint=sdk-cli;"},
    {"type": "text", "text": "You are a Claude agent, built on Anthropic's Claude Agent SDK."},
    {"type": "text", "text": "Sei AgentDeck, costruito da HoneyLabs.", "cache_control": {"type": "ephemeral"}},
]


class AdaptTests(unittest.TestCase):
    def test_fixed_lines_and_params_go_away(self):
        body = {"model": "claude-x", "system": SYSTEM, "messages": [{"role": "user", "content": "ciao"}],
                "context_management": {}, "output_config": {"effort": "high"}, "metadata": {"user_id": "u"},
                "max_tokens": 100, "stream": True}
        out = mp.adapt(body, mp.DEFAULTS)
        self.assertEqual(out["model"], "MiniMax-M3")
        self.assertEqual([b["text"] for b in out["system"]], ["Sei AgentDeck, costruito da HoneyLabs."])
        self.assertEqual(out["system"][0]["cache_control"], {"type": "ephemeral"})
        for k in ("context_management", "output_config", "metadata"):
            self.assertNotIn(k, out)
        self.assertEqual(out["messages"], body["messages"])  # i messaggi non si toccano
        self.assertNotIn("Claude agent", json.dumps(out))

    def test_string_system(self):
        out = mp.adapt({"system": "You are Claude Code, Anthropic's official CLI for Claude.\nSei AgentDeck."},
                       mp.DEFAULTS)
        self.assertEqual(out["system"], "Sei AgentDeck.")


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key = Path(self.tmp.name) / "minimax.key"
        self.api = claude_probe.FakeApi().__enter__()
        self.seen_headers = []
        api = self.api
        original = api.server.RequestHandlerClass.do_POST
        outer = self

        def do_post(handler):
            outer.seen_headers.append({k.lower(): v for k, v in handler.headers.items()})
            return original(handler)

        api.server.RequestHandlerClass.do_POST = do_post
        self.logs = []
        cfg = dict(mp.DEFAULTS, upstream=f"http://127.0.0.1:{api.port}/anthropic", key_file=str(self.key))
        self.proxy = mp.make_server(cfg, self.logs.append, port=0)
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.proxy.server_address[1]}"

    def tearDown(self):
        self.proxy.shutdown()
        self.proxy.server_close()
        self.api.__exit__(None, None, None)
        self.tmp.cleanup()

    def post(self, path, body, headers=None):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), method="POST",
                                     headers=dict({"content-type": "application/json", "x-api-key": "locale",
                                                   "anthropic-beta": "claude-code-20250219"}, **(headers or {})))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read().decode()

    def test_missing_key_is_a_clear_error(self):
        code, text = self.post("/v1/messages", {"stream": True, "messages": []})
        self.assertEqual(code, 401)
        self.assertIn("minimax.key", text)
        self.assertEqual(self.api.requests, [])

    def test_forwards_adapted_request_with_key_and_streams_back(self):
        self.key.write_text("chiave-di-prova\n")
        body = {"model": "claude-x", "system": SYSTEM, "messages": [], "stream": True, "context_management": {}}
        code, text = self.post("/v1/messages?beta=true", body)
        self.assertEqual(code, 200)
        self.assertIn("event: message_start", text)  # lo streaming del finto MiniMax arriva intero
        sent = self.api.requests[0]
        self.assertEqual(sent["model"], "MiniMax-M3")
        self.assertNotIn("Claude agent", json.dumps(sent))
        self.assertNotIn("context_management", sent)
        h = self.seen_headers[0]
        self.assertEqual(h["x-api-key"], "chiave-di-prova")
        self.assertEqual(h["authorization"], "Bearer chiave-di-prova")
        self.assertNotIn("anthropic-beta", h)
        self.assertEqual(self.logs[0]["status"], 200)
        self.assertNotIn("chiave", json.dumps(self.logs))  # il registro non contiene né chiave né contenuti

    def test_count_tokens_is_answered_locally(self):
        code, text = self.post("/v1/messages/count_tokens", {"messages": [{"role": "user", "content": "x" * 400}]})
        self.assertEqual(code, 200)
        self.assertGreater(json.loads(text)["input_tokens"], 50)
        self.assertEqual(self.api.requests, [])

    def test_health(self):
        with urllib.request.urlopen(self.url + "/health", timeout=5) as r:
            data = json.loads(r.read())
        self.assertEqual((data["ok"], data["key_present"]), (True, False))


if __name__ == "__main__":
    unittest.main()
