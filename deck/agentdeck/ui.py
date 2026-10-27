"""Server della pagina dello schermo della Deck (O15.T3, ADR-0003): l'interfaccia effimera che Chromium mostra in kiosk.

Si avvia con `deck ui`, dal servizio agentdeck-ui-server (utente agent). Ascolta solo su 127.0.0.1 (INV-5) e serve:
- la pagina dello schermo, deck/ui/index.html;
- un'API che passa per le stesse schermate di deck: ogni azione ha l'anteprima e la conferma che ha per l'agente,
  e finisce nel registro come le chiamate dalla riga di comando (identificatore agentdeck);
- la retroilluminazione, che lo schermo calmo abbassa e un tocco rialza.
L'API vuole il codice che il server scrive a ogni avvio in /run/agentdeck-ui.token, leggibile solo da agent e
dall'utente del browser (deckui): un altro processo della Deck, per esempio un servizio dell'utente, non può aprire
o chiudere sessioni da qui. Allo schermo arrivano solo le schermate di UI_PATHS.
Documentazione: docs/interfacce.md.
"""
from __future__ import annotations

import hmac
import json
import re
import secrets
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from . import cli
from .components import all_components
from .engine import Deck

HOST = "127.0.0.1"
PORT = 8790
TOKEN_FILE = Path("/run/agentdeck-ui.token")
PAGE = Path(__file__).resolve().parent.parent / "ui" / "index.html"
UI_PATHS = ("/claude",)
NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
MAX_BODY = 4096
MAX_VALUE = 200
BACKLIGHT = Path("/sys/class/backlight")
DIM = 0.08  # frazione della luce piena quando lo schermo è calmo da un po'
HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
           "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                      "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'"}


def call(argv: list, deck_factory=lambda: Deck(all_components())) -> dict:
    """Una chiamata a deck come dalla riga di comando, con l'esito nel registro."""
    result, _ = cli.render(deck_factory(), argv)
    cli.log_call(result, argv)
    return result


def action_argv(body: dict) -> Optional[list]:
    """La chiamata a deck per un'azione dello schermo, o None se non è ammessa."""
    path, action_id, params = body.get("path"), body.get("action"), body.get("params") or {}
    if path not in UI_PATHS or not isinstance(action_id, str) or not NAME.fullmatch(action_id):
        return None
    if not isinstance(params, dict):
        return None
    argv = [path, action_id]
    for key, value in params.items():
        if not isinstance(key, str) or not NAME.fullmatch(key) or not isinstance(value, str):
            return None
        if len(value) > MAX_VALUE or any(c in value for c in "\n\r\0"):
            return None
        argv.append(f"{key}={value}")
    return argv


def address() -> Optional[str]:
    """L'indirizzo della Deck sulla rete di casa, per la riga di stato."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # nessun pacchetto parte: serve solo a scegliere l'interfaccia
            return s.getsockname()[0]
    except OSError:
        return None


def backlight(level: str, base: Path = BACKLIGHT, run=subprocess.run) -> Optional[int]:
    """Porta la luce dello schermo a "full" o "dim". Restituisce il valore scritto, o None."""
    devices = sorted(base.glob("*"))
    if not devices or level not in ("full", "dim"):
        return None
    dev = devices[0]
    try:
        top = int((dev / "max_brightness").read_text())
    except (OSError, ValueError):
        return None
    value = top if level == "full" else max(1, int(top * DIM))
    done = run(["sudo", "-n", "tee", str(dev / "brightness")], input=f"{value}\n", capture_output=True, text=True)
    return value if done.returncode == 0 else None


class Handler(BaseHTTPRequestHandler):
    server_version = "agentdeck-ui"
    token = ""
    deck_factory = staticmethod(lambda: Deck(all_components()))
    page = PAGE
    set_backlight = staticmethod(backlight)

    def log_message(self, fmt, *args):  # le azioni vanno già nel registro con cli.log_call
        pass

    def _send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        for k, v in HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data: dict) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _allowed(self) -> bool:
        host, port = self.headers.get("Host", ""), self.server.server_address[1]
        if host not in (f"{HOST}:{port}", f"localhost:{port}"):  # niente pagine di altri siti via DNS
            self._json(403, {"error": "host"})
            return False
        given = self.headers.get("X-Deck-Token", "")
        if not self.token or not hmac.compare_digest(given, self.token):
            self._json(401, {"error": "token"})
            return False
        return True

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            try:
                return self._send(200, self.page.read_bytes(), "text/html; charset=utf-8")
            except OSError:
                return self._json(500, {"error": "page"})
        if not self._allowed():
            return
        if url.path == "/api/screen":
            path = (parse_qs(url.query).get("path") or [""])[0]
            if path not in UI_PATHS:
                return self._json(404, {"error": "path"})
            return self._json(200, call([path], self.deck_factory))
        if url.path == "/api/home":
            screen = call(["/claude"], self.deck_factory)
            return self._json(200, {"host": socket.gethostname(), "address": address(),
                                    "sessions": (screen.get("data") or {}).get("counts")})
        return self._json(404, {"error": "path"})

    def do_POST(self):
        if not self._allowed():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length)) if 0 < length <= MAX_BODY else None
        except (ValueError, OSError):
            body = None
        if not isinstance(body, dict):
            return self._json(400, {"error": "body"})
        url = urlparse(self.path)
        if url.path == "/api/action":
            argv = action_argv(body)
            if argv is None:
                return self._json(400, {"error": "action"})
            return self._json(200, call(argv, self.deck_factory))
        if url.path == "/api/backlight":
            return self._json(200, {"value": self.set_backlight(str(body.get("level")))})
        return self._json(404, {"error": "path"})


def serve(token_file: Path = TOKEN_FILE) -> int:
    """Avvia il server: nuovo codice a ogni avvio, nel file che systemd ha preparato con i permessi giusti."""
    token = secrets.token_hex(16)
    token_file.write_text(token)
    Handler.token = token
    with ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()
    return 0
