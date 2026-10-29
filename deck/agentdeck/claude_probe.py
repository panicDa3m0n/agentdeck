"""Prova degli agganci di Claude Code da cui dipende AgentDeck, senza rete e senza chiavi (task O18.T2).

Lancia `claude -p` contro un finto server API su 127.0.0.1 che risponde con un copione: chiede un comando Bash
"canarino" che le regole deny gestite devono bloccare, poi un echo innocuo che in bypass deve passare senza
richieste, poi chiude. Dalle richieste registrate e dal risultato JSON verifica: hook di inizio sessione, regole
deny, guardia (hook PreToolUse), evento PermissionRequest (O19), bypass, opzioni --system-prompt, --tools, --mcp-config e --strict-mcp-config, codice di uscita. Si usa prima
di passare a una versione nuova di Claude Code (agentdeck/claude_version.py) e per verificare quella attiva.
Le uscite di Claude Code sono testo esterno: solo nei dati (INV-4). Documentazione: docs/claude-code.md.
"""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

CANARY = "echo agentdeck-deny-canary"   # bloccato da Bash(*agentdeck-deny-canary*) nelle impostazioni gestite
ALLOWED = "cd /opt && echo agentdeck-probe-ok journalctl"  # journalctl: la guardia aggiunge il rimando a deck logs
PROMPT = "Sei la prova degli agganci di AgentDeck."
TIMEOUT_S = 180


def _events(model: str, block: dict, stop: str) -> list:
    start = dict(block)
    delta = None
    if block["type"] == "tool_use":
        start["input"] = {}
        delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
    elif block["type"] == "text":
        start["text"] = ""
        delta = {"type": "text_delta", "text": block["text"]}
    return [
        ("message_start", {"type": "message_start", "message": {
            "id": "msg_probe", "type": "message", "role": "assistant", "model": model, "content": [],
            "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}}),
        ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": start}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None},
                           "usage": {"output_tokens": 1}}),
        ("message_stop", {"type": "message_stop"}),
    ]


class FakeApi:
    """Finto server dell'API Messages: risponde in streaming con un copione e registra le richieste."""

    def __init__(self):
        self.requests: list = []
        self.script = [
            {"type": "tool_use", "id": "toolu_canary", "name": "Bash",
             "input": {"command": CANARY, "description": "probe"}},
            {"type": "tool_use", "id": "toolu_allowed", "name": "Bash",
             "input": {"command": ALLOWED, "description": "probe"}},
            {"type": "text", "text": "probe done"},
        ]
        api = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("content-length", 0)) or 0)
                try:
                    req = json.loads(body or b"{}")
                except ValueError:
                    req = {}
                if "count_tokens" in self.path:
                    self.send_response(200)
                    self.send_header("content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"input_tokens":10}')
                    return
                api.requests.append(req)
                block = api.script[min(len(api.requests), len(api.script)) - 1] if req.get("stream") else \
                    api.script[-1]
                stop = "tool_use" if block["type"] == "tool_use" else "end_turn"
                model = req.get("model", "probe")
                if not req.get("stream"):  # richieste di servizio (titoli, riassunti): una risposta di testo
                    self.send_response(200)
                    self.send_header("content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"id": "msg_probe", "type": "message", "role": "assistant",
                                                 "model": model, "content": [{"type": "text", "text": "probe"}],
                                                 "stop_reason": "end_turn", "stop_sequence": None,
                                                 "usage": {"input_tokens": 1, "output_tokens": 1}}).encode())
                    api.requests.pop()
                    return
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.end_headers()
                for event, data in _events(model, block, stop):
                    self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
                    self.wfile.flush()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def _tool_results(requests: list) -> dict:
    results = {}
    for req in requests:
        for message in req.get("messages", []):
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") == "tool_result":
                    text = block.get("content")
                    if isinstance(text, list):
                        text = " ".join(str(x.get("text", "")) for x in text if isinstance(x, dict))
                    results[block.get("tool_use_id")] = {"is_error": bool(block.get("is_error")),
                                                         "text": str(text)[:500]}
    return results


def _all_text(req: dict) -> str:
    parts = []
    for message in req.get("messages", []):
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return "\n".join(parts)


def _has(binary: Path, needle: bytes) -> bool:
    try:
        with open(binary, "rb") as f:
            tail = b""
            while chunk := f.read(1 << 20):
                if needle in tail + chunk:
                    return True
                tail = chunk[-len(needle):]
    except OSError:
        pass
    return False


def probe(binary: Path, deck: str = "/usr/local/bin/deck", timeout: float = TIMEOUT_S) -> dict:
    """Prova un binario di Claude Code. Restituisce i controlli, ognuno con ok, e ok complessivo."""
    with FakeApi() as api, tempfile.TemporaryDirectory(prefix="agentdeck-probe-") as work:
        mcp = Path(work) / "mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {"deck": {"type": "stdio", "command": deck, "args": ["mcp"]}}}))
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN")}
        env.update({"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{api.port}", "ANTHROPIC_API_KEY": "agentdeck-probe",
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})
        argv = [str(binary), "-p", "probe", "--output-format", "json", "--permission-mode", "bypassPermissions",
                "--system-prompt", PROMPT, "--tools", "Bash", "--mcp-config", str(mcp), "--strict-mcp-config"]
        try:
            out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=work, env=env,
                                 stdin=subprocess.DEVNULL)
            code, stdout, stderr = out.returncode, out.stdout, out.stderr
        except (OSError, subprocess.TimeoutExpired) as e:
            code, stdout, stderr = 124, "", str(e)
        requests = list(api.requests)
    result: Optional[dict] = None
    for line in reversed(stdout.strip().splitlines()):
        try:
            result = json.loads(line)
            break
        except ValueError:
            continue
    tools = _tool_results(requests)
    first = requests[0] if requests else {}
    system = first.get("system")
    system_text = system if isinstance(system, str) else " ".join(
        str(b.get("text", "")) for b in (system or []) if isinstance(b, dict))
    tool_names = [t.get("name") for t in first.get("tools", [])]
    canary = tools.get("toolu_canary", {})
    allowed = tools.get("toolu_allowed", {})
    denials = (result or {}).get("permission_denials") or []
    checks = [
        {"check": "exit code 0 with a JSON result", "ok": code == 0 and result is not None},
        {"check": "our system prompt replaces the default one",
         "ok": PROMPT in system_text and "interactive agent" not in system_text},
        {"check": "SessionStart hook adds AgentDeck context", "ok": "AgentDeck session start" in _all_text(first)},
        {"check": "--tools and --strict-mcp-config limit the tools",
         "ok": "Bash" in tool_names and "Edit" not in tool_names
         and all(n == "Bash" or str(n).startswith("mcp__deck__") or n == "DeferredToolPlaceholder"
                 for n in tool_names) and any(str(n).startswith("mcp__deck__") for n in tool_names)},
        {"check": "managed deny blocks the canary command",
         "ok": canary.get("is_error") is True},  # un echo eseguito non dà mai errore
        {"check": "the guard (PreToolUse hook) adds its hint to an allowed command",
         "ok": len(requests) >= 3 and "deck logs query" in _all_text(requests[2])},
        {"check": "the PermissionRequest hook event exists in the binary", "ok": _has(binary, b"PermissionRequest")},
        {"check": "bypass runs an ordinary command without asking",
         "ok": allowed.get("is_error") is False and "agentdeck-probe-ok" in allowed.get("text", "")
         and not any("agentdeck-probe-ok" in json.dumps(d) for d in denials)},
    ]
    return {"ok": all(c["ok"] for c in checks), "checks": checks, "binary": str(binary), "exit_code": code,
            "requests": len(requests), "tool_results": tools, "permission_denials": denials,
            "stderr": stderr[-2000:], "tool_names": tool_names}
