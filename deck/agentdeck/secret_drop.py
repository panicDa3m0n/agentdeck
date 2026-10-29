"""Richiesta web monouso per i segreti del proprietario (O23.T1): il valore va dal browser al file, mai in chat.

`deck secret request name=<segreto>` prepara la richiesta (token casuale, indirizzo della rete di casa, scadenza) in
$XDG_STATE_HOME/agentdeck/secret-request.json (600) e avvia questo modulo come unità di systemd a tempo,
agentdeck-segreto. Il server ascolta solo sull'indirizzo privato della Deck nella rete di casa (mai su internet,
INV-5), risponde solo all'indirizzo con il token, accetta un solo valore valido entro la scadenza e pochi tentativi,
lo scrive nel file del segreto con permessi 600 e si ferma. Il valore non compare mai in schermate, registri,
argomenti dei processi o chat (INV-4, INV-6): il registro secret-requests.jsonl tiene solo ora, segreto, esito e
indirizzo di chi ha risposto. Solo libreria standard, così si avvia anche come script. Schermata:
agentdeck/components/secret.py. Documentazione: docs/segreti.md.
"""
from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import secrets
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs

PORT = 8792
TTL_S = 900
MAX_BAD = 5        # valori non validi prima di chiudere
MAX_STRAY = 20     # richieste a indirizzi sbagliati prima di chiudere
MAX_BODY = 4096
UNIT = "agentdeck-segreto"

_KEY = re.compile(r"[\x21-\x7e]{16,512}")
_TG_TOKEN = re.compile(r"[0-9]{6,12}:[A-Za-z0-9_-]{30,64}")
_CHAT_ID = re.compile(r"-?[0-9]{1,20}")


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "agentdeck"


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck"


# Segreti che il proprietario può consegnare: file, titolo della pagina e campi del modulo.
SLOTS = {
    "minimax": {"file": "minimax.key", "title": "Chiave API MiniMax",
                "fields": [("key", "Chiave API MiniMax", "password")]},
    "telegram": {"file": "telegram.json", "title": "Bot Telegram",
                 "fields": [("token", "Token del bot (da BotFather)", "password"),
                            ("chat_id", "Il tuo chat id", "text")]},
}


def slot_path(name: str) -> Path:
    return config_dir() / SLOTS[name]["file"]


def presence(name: str) -> dict:
    """Se il segreto c'è, con dimensione, permessi e data: mai il contenuto."""
    path = slot_path(name)
    info: dict = {"name": name, "path": str(path), "present": False}
    try:
        st = path.stat()
    except OSError:
        return info
    info.update({"present": st.st_size > 0, "bytes": st.st_size, "mode": oct(st.st_mode & 0o777),
                 "modified": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime))})
    return info


class Refused(ValueError):
    """Un valore non valido: code è stabile, message è per la pagina del proprietario."""

    def __init__(self, code: str, message: str):
        super().__init__(code)
        self.code, self.message = code, message


def content_for(name: str, form: dict) -> str:
    """Il contenuto del file per i valori del modulo, già controllati."""
    value = {k: (form.get(k) or [""])[0].strip() for k, _, _ in SLOTS[name]["fields"]}
    if name == "minimax":
        if not _KEY.fullmatch(value["key"]):
            raise Refused("bad_key", "La chiave deve essere una riga sola, senza spazi, di almeno 16 caratteri.")
        return value["key"] + "\n"
    if not _TG_TOKEN.fullmatch(value["token"]):
        raise Refused("bad_token", "Il token del bot ha la forma 123456789:ABC… (numero, due punti, codice).")
    if not _CHAT_ID.fullmatch(value["chat_id"]):
        raise Refused("bad_chat_id", "Il chat id è un numero, per esempio 123456789.")
    current: dict = {}
    try:
        loaded = json.loads(slot_path(name).read_text())
        if isinstance(loaded, dict):
            current = loaded  # le altre impostazioni del ponte restano
    except (OSError, ValueError):
        pass
    current.update({"token": value["token"], "chat_id": int(value["chat_id"])})
    return json.dumps(current, indent=2) + "\n"


def write_secret(path: Path, content: str) -> None:
    """Scrittura atomica con permessi 600 fin dall'inizio, in una cartella 700."""
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)


# ---- La richiesta in corso e il registro

def request_file() -> Path:
    return state_dir() / "secret-request.json"


def log_file() -> Path:
    return state_dir() / "secret-requests.jsonl"


def new_request(name: str, host: str, port: int = PORT, ttl_s: int = TTL_S, now: Optional[float] = None) -> dict:
    now = time.time() if now is None else now
    req = {"name": name, "token": secrets.token_urlsafe(24), "host": host, "port": port,
           "created_at": now, "expires_at": now + ttl_s}
    write_secret(request_file(), json.dumps(req) + "\n")
    return req


def load_request() -> Optional[dict]:
    try:
        req = json.loads(request_file().read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(req, dict) or req.get("name") not in SLOTS or not isinstance(req.get("token"), str):
        return None
    return req


def clear_request() -> None:
    request_file().unlink(missing_ok=True)


def url(req: dict) -> str:
    return f"http://{req['host']}:{req['port']}/{req['token']}"


def record(name: str, outcome: str, peer: Optional[str] = None) -> None:
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "name": name, "outcome": outcome}
    if peer:
        entry["from"] = peer
    path = log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def history(limit: int = 5) -> list:
    try:
        lines = log_file().read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return list(reversed(out))


def lan_address(run: Callable = subprocess.run) -> Optional[str]:
    """L'indirizzo IPv4 privato con cui la Deck esce nella rete di casa; None se non è privato (INV-5)."""
    try:
        out = run(["ip", "-j", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5)
        src = json.loads(out.stdout or "[]")[0].get("prefsrc")
        ip = ipaddress.ip_address(src)
    except (OSError, ValueError, IndexError, TypeError, AttributeError, subprocess.SubprocessError):
        return None
    return str(ip) if ip.is_private and not ip.is_loopback else None


# ---- Il server monouso

_PAGE = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentDeck: {title}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:32rem;margin:2rem auto;padding:0 1rem;color:#222;
background:#fafafa}}label{{display:block;margin:1rem 0 .3rem;font-weight:600}}input{{width:100%;box-sizing:border-box;
padding:.6rem;font:inherit;border:1px solid #888;border-radius:.4rem}}button{{margin-top:1.2rem;padding:.7rem 1.2rem;
font:inherit;border:0;border-radius:.4rem;background:#1a5fb4;color:#fff}}.err{{color:#a51d2d}}.note{{color:#555;
font-size:.9rem}}@media(prefers-color-scheme:dark){{body{{background:#1e1e1e;color:#eee}}input{{background:#2a2a2a;
color:#eee}}.note{{color:#aaa}}.err{{color:#f66}}}}</style></head><body>{body}</body></html>"""


def form_page(name: str, error: Optional[str] = None) -> str:
    slot = SLOTS[name]
    fields = "".join(f'<label for="{k}">{html.escape(label)}</label><input id="{k}" name="{k}" type="{kind}" '
                     f'autocomplete="off" autocapitalize="off" spellcheck="false" required>'
                     for k, label, kind in slot["fields"])
    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    body = (f"<h1>{html.escape(slot['title'])}</h1><p>AgentDeck chiede questo segreto. Il valore va direttamente nel "
            f"file della Deck, con permessi 600: l'agente non lo vede e non passa dalla chat.</p>{err}"
            f'<form method="post">{fields}<button type="submit">Invia</button></form>'
            f'<p class="note">Il link vale una volta sola e scade fra pochi minuti.</p>')
    return _PAGE.format(title=html.escape(slot["title"]), body=body)


def done_page(name: str) -> str:
    return _PAGE.format(title=html.escape(SLOTS[name]["title"]),
                        body="<h1>Ricevuto</h1><p>Il segreto è sulla Deck. Puoi chiudere questa pagina: il link non "
                             "vale più.</p>")


class _Handler(BaseHTTPRequestHandler):
    server_version = "AgentDeck"
    sys_version = ""
    timeout = 15  # un client che apre la connessione e tace non blocca il server
    drop: "Drop"

    def log_message(self, format, *args):  # noqa: A002 - il percorso contiene il token: niente su stderr
        pass

    def _send(self, code: int, page: str) -> None:
        body = page.encode("utf-8")
        self.send_response(code)
        for k, v in (("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body))),
                     ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                     ("X-Frame-Options", "DENY"), ("X-Content-Type-Options", "nosniff"),
                     ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _ours(self) -> bool:
        if secrets.compare_digest(self.path.split("?")[0], "/" + self.drop.req["token"]):
            return True
        self.drop.stray += 1
        if self.drop.stray >= MAX_STRAY:
            self.drop.outcome = "too_many_attempts"
        self._send(404, _PAGE.format(title="AgentDeck", body="<h1>Non trovato</h1>"))
        return False

    def do_GET(self):
        if self._ours():
            self._send(200, form_page(self.drop.req["name"]))

    def do_POST(self):
        if not self._ours():
            return
        name = self.drop.req["name"]
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self.drop.bad += 1
            self._send(413, form_page(name, "Valore troppo lungo."))
        else:
            form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"), max_num_fields=8)
            try:
                content = content_for(name, form)
            except Refused as e:
                self.drop.bad += 1
                self._send(400, form_page(name, e.message))
            else:
                write_secret(slot_path(name), content)
                self.drop.outcome, self.drop.peer = "received", self.client_address[0]
                self._send(200, done_page(name))
                return
        if self.drop.bad >= MAX_BAD:
            self.drop.outcome = "too_many_attempts"


class Drop:
    """Un server per una richiesta: si ferma al primo valore valido, alla scadenza o dopo troppi tentativi."""

    def __init__(self, req: dict, host: Optional[str] = None, port: Optional[int] = None):
        self.req, self.bad, self.stray = req, 0, 0
        self.outcome: Optional[str] = None
        self.peer: Optional[str] = None
        handler = type("Handler", (_Handler,), {"drop": self})
        self.server = HTTPServer((host or req["host"], req["port"] if port is None else port), handler)
        self.server.timeout = 0.5

    @property
    def port(self) -> int:
        return self.server.server_address[1]

    def run(self, now: Callable[[], float] = time.time) -> str:
        try:
            while self.outcome is None and now() < self.req["expires_at"]:
                self.server.handle_request()
        finally:
            self.server.server_close()
        outcome = self.outcome or "expired"
        clear_request()
        record(self.req["name"], outcome, self.peer)
        return outcome


def serve() -> int:
    """Avvio dall'unità agentdeck-segreto: legge la richiesta in corso e la serve."""
    req = load_request()
    if req is None:
        return 1
    if time.time() >= req["expires_at"]:
        clear_request()
        record(req["name"], "expired")
        return 0
    Drop(req).run()
    return 0


if __name__ == "__main__":
    sys.exit(serve())
