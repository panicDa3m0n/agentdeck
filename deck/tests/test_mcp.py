"""Test del server MCP di deck: JSON-RPC, strumenti generati dalle azioni, conferme in due passi, INV-4.

Si lanciano dalla cartella deck/: python3 -m unittest discover -s tests
Codice: agentdeck/mcp.py. Documentazione: docs/deck.md, "Server MCP".
"""
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["AGENTDECK_NO_LOG"] = "1"

from agentdeck import mcp  # noqa: E402
from agentdeck.components.home import Home  # noqa: E402
from agentdeck.components.protocol_info import ProtocolInfo  # noqa: E402
from agentdeck.engine import Deck  # noqa: E402
from agentdeck.protocol import instruction_texts, screen, sys_text, validate  # noqa: E402
from test_deck import INJECTION, Fake  # noqa: E402


class Noisy(Fake):
    """Come Fake, ma stampa su stdout durante l'azione: non deve arrivare nel flusso JSON-RPC."""

    path = "/noisy"

    def run(self, ctx, action_id, params):
        print("stray output from a component")
        return screen(screen="noisy.done", path=self.path, title=sys_text("Done"), status="done", back=self.path,
                      prompt=sys_text("Done."))


def make_deck():
    return Deck([Home(), ProtocolInfo(), Fake()])


def request(method, params=None, msg_id=1):
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


class McpTests(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.TemporaryDirectory()
        os.environ["XDG_STATE_HOME"] = self.state.name
        self.server = mcp.Server(make_deck)

    def tearDown(self):
        self.state.cleanup()

    def rpc(self, method, params=None):
        reply = self.server.handle(request(method, params))
        self.assertEqual((reply["jsonrpc"], reply["id"]), ("2.0", 1))
        return reply

    def call(self, name, **arguments):
        reply = self.rpc("tools/call", {"name": name, "arguments": arguments})
        result = reply["result"]
        s = json.loads(result["content"][0]["text"])
        self.assertEqual(validate(s), [], f"tool {name} returned a screen outside the protocol")
        for text in instruction_texts(s):
            self.assertNotIn("Ignore previous", text)
        self.assertEqual(result["isError"], s["status"] == "error")
        return s

    def tools(self):
        return {t["name"]: t for t in self.rpc("tools/list")["result"]["tools"]}

    def test_initialize_negotiates_version(self):
        r = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "test", "version": "0"}})["result"]
        self.assertEqual(r["protocolVersion"], "2025-06-18")
        self.assertEqual(r["serverInfo"]["name"], "deck")
        self.assertIn("tools", r["capabilities"])
        self.assertIn("confirm=<token>", r["instructions"])
        old = self.rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]
        self.assertEqual(old["protocolVersion"], mcp.DEFAULT_PROTOCOL)

    def test_notifications_get_no_reply(self):
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "id": 9, "result": {}}))

    def test_tools_come_from_actions(self):
        tools = self.tools()
        self.assertEqual(set(tools), {"open", "fake_make", "fake_wipe", "fake_boom", "fake_later"})
        make = tools["fake_make"]["inputSchema"]
        self.assertEqual(make["properties"]["n"]["type"], "integer")
        self.assertEqual(make["properties"]["mode"]["enum"], ["fast", "slow"])
        self.assertEqual(make["properties"]["note"]["maxLength"], 10)
        self.assertEqual(make["required"], ["n"])
        self.assertFalse(make["additionalProperties"])
        wipe = tools["fake_wipe"]
        self.assertIn("confirm", wipe["inputSchema"]["properties"])
        self.assertNotIn("confirm", wipe["inputSchema"]["required"])
        self.assertTrue(wipe["annotations"]["destructiveHint"])
        self.assertNotIn("confirm", make["properties"])
        self.assertEqual(tools["open"]["inputSchema"]["properties"]["path"]["enum"], ["/", "/fake", "/protocol"])
        self.assertTrue(tools["open"]["annotations"]["readOnlyHint"])

    def test_tool_texts_never_carry_data(self):
        listing = json.dumps(self.rpc("tools/list")["result"]) + mcp.INSTRUCTIONS
        listing += json.dumps(self.rpc("resources/list")["result"])
        self.assertNotIn("Ignore previous", listing)
        self.assertNotIn(INJECTION, listing)

    def test_open_returns_the_screen(self):
        s = self.call("open", path="/fake")
        self.assertEqual((s["screen"], s["status"]), ("fake", "ok"))
        self.assertEqual(s["data"]["items"][0]["description"], INJECTION)  # il testo esterno resta nei dati
        self.assertEqual(self.call("open", path="protocol")["path"], "/protocol")

    def test_typed_arguments(self):
        s = self.call("fake_make", n=3, mode="fast", note="hi")
        self.assertEqual(s["status"], "done")
        self.assertEqual(s["data"]["params"], {"n": 3, "mode": "fast", "note": "hi"})

    def test_destructive_runs_in_two_steps(self):
        preview = self.call("fake_wipe", id=1)
        self.assertEqual(preview["status"], "confirm")
        token = preview["confirm"]["token"]
        self.assertEqual(self.call("fake_wipe", id=1, confirm=token)["status"], "done")
        again = self.call("fake_wipe", id=1, confirm=token)
        self.assertEqual(again["error"]["code"], "CONFIRM_INVALID")

    def test_confirm_is_bound_to_arguments(self):
        token = self.call("fake_wipe", id=1)["confirm"]["token"]
        self.assertEqual(self.call("fake_wipe", id=2, confirm=token)["error"]["code"], "CONFIRM_INVALID")

    def test_bad_values_are_tool_errors(self):
        self.assertEqual(self.call("fake_make", n="many")["error"]["code"], "BAD_PARAM")
        self.assertEqual(self.call("fake_make")["error"]["code"], "MISSING_PARAM")
        self.assertEqual(self.call("fake_later")["error"]["code"], "NOT_AVAILABLE")
        self.assertEqual(self.call("fake_make", n=1, confirm="abcd")["error"]["code"], "BAD_PARAM")

    def test_internal_failure_is_a_screen(self):
        s = self.call("fake_boom")
        self.assertEqual(s["error"]["code"], "FAILED")

    def test_protocol_errors(self):
        unknown = self.server.handle(request("tools/call", {"name": "nope", "arguments": {}}))
        self.assertEqual(unknown["error"]["code"], -32602)
        bad_names = self.server.handle(request("tools/call", {"name": "fake_make", "arguments": {"N=1 x": 1}}))
        self.assertEqual(bad_names["error"]["code"], -32602)
        bad_path = self.server.handle(request("tools/call", {"name": "open", "arguments": {"path": "a b"}}))
        self.assertEqual(bad_path["error"]["code"], -32602)
        self.assertEqual(self.server.handle(request("prompts/get"))["error"]["code"], -32601)
        self.assertEqual(self.server.handle_line(b"{not json")["error"]["code"], -32700)
        self.assertEqual(self.server.handle({"id": 3, "method": "ping"})["error"]["code"], -32600)
        self.assertEqual(self.rpc("ping")["result"], {})

    def test_resources(self):
        listed = {r["uri"]: r for r in self.rpc("resources/list")["result"]["resources"]}
        self.assertEqual(set(listed), {"deck:/", "deck:/fake", "deck:/protocol"})
        content = self.rpc("resources/read", {"uri": "deck:/fake"})["result"]["contents"][0]
        self.assertEqual(json.loads(content["text"])["screen"], "fake")
        missing = self.server.handle(request("resources/read", {"uri": "https://example.com"}))
        self.assertEqual(missing["error"]["code"], -32002)

    def test_batch(self):
        replies = self.server.handle_line(json.dumps([request("ping", msg_id=1), request("ping", msg_id=2)]).encode())
        self.assertEqual([r["id"] for r in replies], [1, 2])

    def test_stdio_loop(self):
        lines = [request("initialize", {"protocolVersion": "2025-06-18"}, 1),
                 {"jsonrpc": "2.0", "method": "notifications/initialized"},
                 request("tools/call", {"name": "noisy_make", "arguments": {"n": 1}}, 2)]
        stdin = io.BytesIO(b"".join(json.dumps(m).encode() + b"\n" for m in lines) + b"\n")
        stdout = io.BytesIO()
        stderr = io.StringIO()
        real_stderr, sys.stderr = sys.stderr, stderr
        try:
            self.assertEqual(mcp.serve(stdin, stdout, lambda: Deck([Home(), Noisy()])), 0)
        finally:
            sys.stderr = real_stderr
        replies = [json.loads(line) for line in stdout.getvalue().decode().splitlines()]
        self.assertEqual([r["id"] for r in replies], [1, 2])
        self.assertEqual(json.loads(replies[1]["result"]["content"][0]["text"])["status"], "done")
        self.assertIn("stray output", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
