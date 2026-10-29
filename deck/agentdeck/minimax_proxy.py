"""Intermediario locale fra Claude Code e MiniMax per l'agente interno (task O20.T1, piano punto 1).

L'agente interno usa Claude Code come motore (strumenti deck, guardia, hook) e MiniMax come modello. Claude Code
manda le richieste a ANTHROPIC_BASE_URL=http://127.0.0.1:<porta>; qui ogni richiesta si adatta e si inoltra
all'endpoint di MiniMax compatibile con Anthropic:
- nel prompt di sistema si tolgono la riga fissa di Claude Code ("You are a Claude agent, built on Anthropic's Claude
  Agent SDK." e varianti) e l'intestazione di fatturazione: decisione del proprietario, verso MiniMax l'identità è
  solo quella di AgentDeck, scritta nel prompt di sistema dal sistema (O20.T2);
- il modello diventa quello configurato (di norma MiniMax-M3);
- si tolgono i parametri e le intestazioni che MiniMax non usa (configurabili);
- la chiave si legge dalla Deck (~/.config/agentdeck/minimax.key, 600) a ogni richiesta e non si scrive mai altrove;
- count_tokens si stima qui, perché MiniMax non lo espone.
Le risposte tornano in streaming così come arrivano. Ascolta solo su 127.0.0.1. Il contenuto delle richieste non si
registra: il registro tiene solo ora, percorso, modello, esito e durata.
Configurazione: ~/.config/agentdeck/agente.json. Servizio: claude/agentdeck-agente-proxy.service.
Documentazione: docs/agente-interno.md.
"""
from __future__ import annotations

import http.client
import http.server
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Optional

HOME = Path(os.environ.get("HOME", "/home/agent"))
CONFIG = HOME / ".config" / "agentdeck" / "agente.json"
DEFAULTS = {
    "upstream": "https://api.minimax.io/anthropic",
    "model": "MiniMax-M3",
    "key_file": str(HOME / ".config" / "agentdeck" / "minimax.key"),
    "port": 8791,
    "strip_params": ["context_management", "output_config", "metadata"],
    "strip_headers": ["anthropic-beta", "anthropic-dangerous-direct-browser-access", "x-claude-code-session-id"],
    "timeout_s": 600,
}
# righe fisse che Claude Code mette nel prompt di sistema: verso MiniMax non vanno
FIXED_LINES = [
    re.compile(r"^\s*x-anthropic-billing-header:.*$"),
    re.compile(r"^\s*You are a Claude agent, built on Anthropic's Claude Agent SDK\.\s*$"),
    re.compile(r"^\s*You are Claude Code, Anthropic's official CLI for Claude\.\s*$"),
    re.compile(r"^\s*You are Claude Code, Anthropic's official CLI for Claude, running within the Claude Agent SDK\.\s*$"),
]
HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "proxy-authorization",
               "proxy-authenticate", "host", "content-length", "x-api-key", "authorization", "accept-encoding"}


def load_config(path: Path = CONFIG) -> dict:
    cfg = dict(DEFAULTS)
    try:
        cfg.update(json.loads(path.read_text()))
    except (OSError, ValueError):
        pass
    return cfg


def read_key(cfg: dict) -> Optional[str]:
    try:
        key = Path(cfg["key_file"]).read_text().strip()
    except OSError:
        return None
    return key or None


def _clean_text(text: str) -> str:
    lines = [ln for ln in text.split("\n") if not any(p.match(ln) for p in FIXED_LINES)]
    return "\n".join(lines).strip("\n")


def adapt(body: dict, cfg: dict) -> dict:
    """La richiesta di Claude Code adattata per MiniMax. Non cambia i messaggi: solo sistema, modello, parametri."""
    out = {k: v for k, v in body.items() if k not in cfg["strip_params"]}
    system = out.get("system")
    if isinstance(system, str):
        out["system"] = _clean_text(system)
    elif isinstance(system, list):
        blocks = []
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                text = _clean_text(str(block.get("text", "")))
                if not text.strip():
                    continue
                block = dict(block, text=text)
            blocks.append(block)
        out["system"] = blocks
    if cfg.get("model"):
        out["model"] = cfg["model"]
    return out


def estimate_tokens(body: dict) -> int:
    return max(1, len(json.dumps(body, ensure_ascii=False)) // 4)


class Handler(http.server.BaseHTTPRequestHandler):
    cfg: dict = DEFAULTS
    log = None  # funzione di registro, una riga per richiesta

    def log_message(self, *args):
        pass

    def _reply(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/health"):
            self._reply(200, {"ok": True, "upstream": self.cfg["upstream"], "model": self.cfg["model"],
                              "key_present": read_key(self.cfg) is not None})
            return
        self._reply(404, {"type": "error", "error": {"type": "not_found_error", "message": "not proxied"}})

    def do_POST(self):
        started = time.monotonic()
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            self._reply(400, {"type": "error", "error": {"type": "invalid_request_error", "message": "bad JSON"}})
            return
        path = urllib.parse.urlsplit(self.path).path
        if path.endswith("/count_tokens"):
            self._reply(200, {"input_tokens": estimate_tokens(body)})
            return
        key = read_key(self.cfg)
        if key is None:
            self._reply(401, {"type": "error", "error": {
                "type": "authentication_error",
                "message": "AgentDeck: MiniMax key missing on the Deck (~/.config/agentdeck/minimax.key)"}})
            self._log(path, body, 401, started)
            return
        upstream = urllib.parse.urlsplit(self.cfg["upstream"])
        target = upstream.path.rstrip("/") + path
        query = urllib.parse.urlsplit(self.path).query
        if query and "beta=" not in query:
            target += "?" + query
        data = json.dumps(adapt(body, self.cfg)).encode()
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in HOP_HEADERS and k.lower() not in self.cfg["strip_headers"]}
        headers.update({"x-api-key": key, "authorization": f"Bearer {key}", "content-type": "application/json",
                        "content-length": str(len(data))})
        conn_cls = http.client.HTTPSConnection if upstream.scheme == "https" else http.client.HTTPConnection
        try:
            conn = conn_cls(upstream.netloc, timeout=self.cfg["timeout_s"])
            conn.request("POST", target, body=data, headers=headers)
            resp = conn.getresponse()
        except OSError as e:
            self._reply(502, {"type": "error", "error": {"type": "api_error",
                                                         "message": f"AgentDeck proxy: upstream unreachable ({type(e).__name__})"}})
            self._log(path, body, 502, started)
            return
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in HOP_HEADERS:
                self.send_header(k, v)
        self.send_header("connection", "close")
        self.end_headers()
        try:
            while True:
                chunk = resp.read1(65536) if hasattr(resp, "read1") else resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except OSError:
            pass
        finally:
            conn.close()
        self._log(path, body, resp.status, started)

    def _log(self, path: str, body: dict, status: int, started: float) -> None:
        if self.log:
            self.log({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "path": path, "model": self.cfg["model"],
                      "stream": bool(body.get("stream")), "status": status,
                      "ms": int((time.monotonic() - started) * 1000)})


def make_server(cfg: dict, log=None, port: Optional[int] = None) -> http.server.ThreadingHTTPServer:
    handler = type("ConfiguredHandler", (Handler,), {"cfg": cfg, "log": staticmethod(log) if log else None})
    return http.server.ThreadingHTTPServer(("127.0.0.1", cfg["port"] if port is None else port), handler)


def main() -> int:
    cfg = load_config()
    state = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "agentdeck"
    state.mkdir(parents=True, exist_ok=True)
    log_file = state / "agente-proxy.jsonl"

    def log(entry: dict) -> None:
        try:
            with log_file.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    server = make_server(cfg, log)
    print(f"agentdeck minimax proxy on 127.0.0.1:{server.server_address[1]} -> {cfg['upstream']} ({cfg['model']})",
          flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
