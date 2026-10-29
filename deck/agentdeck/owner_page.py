"""Pagine monouso per le richieste al proprietario: segreti e domande (O23.T1).

Decisione del proprietario del 30/10/2026 (INV-5): ogni richiesta al proprietario genera una pagina HTML semplice,
esposta su internet con un tunnel temporaneo di Cloudflare solo finché arriva il dato, poi tutto si chiude. In
alternativa la pagina resta solo nella rete di casa (via=home).

Due tipi di richiesta, una alla volta:
- secret: il valore va dal browser al file del segreto con permessi 600 e l'agente non lo vede mai (INV-4, INV-6);
  segreti conosciuti (minimax, telegram) con il loro formato, oppure qualunque altro nome in
  ~/.config/agentdeck/secrets/<nome>;
- ask: una domanda con campi (testo, testo lungo, scelta); la risposta torna all'agente come dato, in
  $XDG_STATE_HOME/agentdeck/answers/<id>.json.

`deck secret request` e `deck ask create` (agentdeck/components/secret.py e ask.py) preparano la richiesta in
$XDG_STATE_HOME/agentdeck/owner-request.json (600: token da 192 bit, scadenza) e avviano questo modulo come unità a
tempo agentdeck-pagina, con Launcher. Il server risponde solo all'indirizzo con il token, accetta un solo invio
valido entro la scadenza e pochi tentativi, e con via=internet avvia cloudflared come processo figlio: il tunnel vive
quanto il server. Nessun registro con il percorso del token; il registro owner-requests.jsonl tiene solo ora, tipo,
nome, esito e indirizzo di chi ha risposto. Solo libreria standard, così si avvia anche come script.
Documentazione: docs/richieste.md.
"""
from __future__ import annotations

import html
import ipaddress
import json
import os
import pwd
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs

PORT = 8792
TTL_S = 900
MAX_BAD = 5        # invii non validi prima di chiudere
MAX_STRAY = 20     # richieste a indirizzi sbagliati prima di chiudere
MAX_BODY = 32768
UNIT = "agentdeck-pagina"
VIAS = ("internet", "home")
KINDS = ("secret", "ask")

SLUG = re.compile(r"[a-z][a-z0-9-]{0,31}")
FIELD_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
FIELD_TYPES = ("text", "textarea", "choice")
MAX_FIELDS = 6
MAX_ANSWER = 4000
_PUBLIC = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
_KEY = re.compile(r"[\x21-\x7e]{16,512}")
_GENERIC = re.compile(r"[\x20-\x7e]{1,4096}")
_TG_TOKEN = re.compile(r"[0-9]{6,12}:[A-Za-z0-9_-]{30,64}")
_CHAT_ID = re.compile(r"-?[0-9]{1,20}")


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "agentdeck"


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck"


def cloudflared() -> Optional[str]:
    return os.environ.get("AGENTDECK_CLOUDFLARED") or shutil.which("cloudflared")


# ---- Segreti

# Segreti con un formato conosciuto: file, titolo della pagina e campi del modulo. Gli altri nomi hanno un campo solo.
SLOTS = {
    "minimax": {"file": "minimax.key", "title": "Chiave API MiniMax",
                "fields": [("key", "Chiave API MiniMax", "password")]},
    "telegram": {"file": "telegram.json", "title": "Bot Telegram",
                 "fields": [("token", "Token del bot (da BotFather)", "password"),
                            ("chat_id", "Il tuo chat id", "text")]},
}


def slot_path(name: str) -> Path:
    if name in SLOTS:
        return config_dir() / SLOTS[name]["file"]
    return config_dir() / "secrets" / name


def known_secrets() -> list:
    """I segreti conosciuti più quelli già consegnati con un altro nome."""
    names = list(SLOTS)
    try:
        names += sorted(p.name for p in (config_dir() / "secrets").iterdir() if SLUG.fullmatch(p.name))
    except OSError:
        pass
    return names


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


def _first(form: dict, key: str) -> str:
    return (form.get(key) or [""])[0]


def secret_fields(name: str) -> list:
    if name in SLOTS:
        return SLOTS[name]["fields"]
    return [("value", "Valore", "password")]


def secret_content(name: str, form: dict) -> str:
    """Il contenuto del file del segreto per i valori del modulo, già controllati."""
    if name == "minimax":
        key = _first(form, "key").strip()
        if not _KEY.fullmatch(key):
            raise Refused("bad_key", "La chiave deve essere una riga sola, senza spazi, di almeno 16 caratteri.")
        return key + "\n"
    if name == "telegram":
        token, chat_id = _first(form, "token").strip(), _first(form, "chat_id").strip()
        if not _TG_TOKEN.fullmatch(token):
            raise Refused("bad_token", "Il token del bot ha la forma 123456789:ABC… (numero, due punti, codice).")
        if not _CHAT_ID.fullmatch(chat_id):
            raise Refused("bad_chat_id", "Il chat id è un numero, per esempio 123456789.")
        current: dict = {}
        try:
            loaded = json.loads(slot_path(name).read_text())
            if isinstance(loaded, dict):
                current = loaded  # le altre impostazioni del ponte restano
        except (OSError, ValueError):
            pass
        current.update({"token": token, "chat_id": int(chat_id)})
        return json.dumps(current, indent=2) + "\n"
    value = _first(form, "value").strip()
    if not _GENERIC.fullmatch(value):
        raise Refused("bad_value", "Serve un valore su una riga, con caratteri stampabili, al massimo 4096.")
    return value + "\n"


def write_private(path: Path, content: str) -> None:
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


# ---- Domande

def parse_fields(spec: Optional[str]) -> list:
    """I campi di una domanda, da JSON: [{"name", "label", "type", "options"}]; senza, un testo lungo solo."""
    if not spec:
        return [{"name": "risposta", "label": "Risposta", "type": "textarea"}]
    try:
        raw = json.loads(spec)
    except ValueError:
        raise Refused("bad_fields", "fields must be a JSON list") from None
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_FIELDS:
        raise Refused("bad_fields", "fields must be a JSON list of 1 to 6 objects")
    fields, names = [], set()
    for f in raw:
        if not isinstance(f, dict):
            raise Refused("bad_fields", "each field is an object")
        name, label, kind = f.get("name"), f.get("label", f.get("name")), f.get("type", "text")
        if not isinstance(name, str) or not FIELD_NAME.fullmatch(name) or name in names:
            raise Refused("bad_fields", "field names are unique lowercase identifiers")
        if not isinstance(label, str) or not 1 <= len(label) <= 200 or kind not in FIELD_TYPES:
            raise Refused("bad_fields", "labels are 1 to 200 characters; types are text, textarea, choice")
        field = {"name": name, "label": label, "type": kind}
        if kind == "choice":
            options = f.get("options")
            if (not isinstance(options, list) or not 2 <= len(options) <= 10
                    or not all(isinstance(o, str) and 1 <= len(o) <= 100 for o in options)
                    or len(set(options)) != len(options)):
                raise Refused("bad_fields", "a choice needs 2 to 10 different options of 1 to 100 characters")
            field["options"] = options
        names.add(name)
        fields.append(field)
    return fields


def ask_answer(fields: list, form: dict) -> dict:
    answer = {}
    for f in fields:
        value = _first(form, f["name"]).replace("\r\n", "\n").strip()
        if not value:
            raise Refused("missing", f"Manca la risposta a: {f['label']}")
        if len(value) > MAX_ANSWER:
            raise Refused("too_long", f"Risposta troppo lunga: {f['label']}")
        if f["type"] == "choice" and value not in f["options"]:
            raise Refused("bad_choice", f"Scegli una delle opzioni: {f['label']}")
        answer[f["name"]] = value
    return answer


def answers_dir() -> Path:
    return state_dir() / "answers"


def answer_path(ask_id: str) -> Path:
    return answers_dir() / f"{ask_id}.json"


def load_answer(ask_id: str) -> Optional[dict]:
    if not re.fullmatch(r"[0-9a-f]{6}", ask_id or ""):
        return None
    try:
        item = json.loads(answer_path(ask_id).read_text())
    except (OSError, ValueError):
        return None
    return item if isinstance(item, dict) else None


def recent_answers(limit: int = 5) -> list:
    try:
        files = sorted(answers_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    except OSError:
        return []
    out = []
    for p in files:
        item = load_answer(p.stem)
        if item:
            out.append(item)
    return out


# ---- La richiesta in corso e il registro

def request_file() -> Path:
    return state_dir() / "owner-request.json"


def log_file() -> Path:
    return state_dir() / "owner-requests.jsonl"


def new_request(kind: str, via: str, host: str, *, port: int = PORT, ttl_s: int = TTL_S, name: Optional[str] = None,
                title: Optional[str] = None, question: Optional[str] = None, fields: Optional[list] = None,
                now: Optional[float] = None) -> dict:
    now = time.time() if now is None else now
    req = {"id": secrets.token_hex(3), "kind": kind, "via": via, "token": secrets.token_urlsafe(24), "host": host,
           "port": port, "created_at": now, "expires_at": now + ttl_s, "public_url": None}
    if kind == "secret":
        req["name"] = name
    else:
        req.update({"title": title, "question": question, "fields": fields})
        write_private(answer_path(req["id"]), json.dumps(
            {"id": req["id"], "status": "open", "title": title, "question": question, "fields": fields,
             "created": _stamp(now), "answer": None}, ensure_ascii=False, indent=2) + "\n")
    write_private(request_file(), json.dumps(req, ensure_ascii=False) + "\n")
    return req


def load_request() -> Optional[dict]:
    try:
        req = json.loads(request_file().read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(req, dict) or req.get("kind") not in KINDS or not isinstance(req.get("token"), str):
        return None
    return req


def update_request(**changes) -> None:
    req = load_request()
    if req is not None:
        req.update(changes)
        write_private(request_file(), json.dumps(req, ensure_ascii=False) + "\n")


def label(req: dict) -> str:
    return req["name"] if req["kind"] == "secret" else req["id"]


def link(req: dict) -> Optional[str]:
    """Il link per il proprietario: dal tunnel con via=internet, dalla rete di casa con via=home."""
    base = req.get("public_url") if req["via"] == "internet" else f"http://{req['host']}:{req['port']}"
    return f"{base}/{req['token']}" if base else None


def finish(req: dict, outcome: str, peer: Optional[str] = None, answer: Optional[dict] = None) -> None:
    """Chiude la richiesta: stato tolto, registro, e per una domanda il suo file con l'esito."""
    current = load_request()
    if current is not None and current.get("token") == req["token"]:
        request_file().unlink(missing_ok=True)
    entry = {"time": _stamp(time.time()), "kind": req["kind"], "name": label(req), "outcome": outcome}
    if peer:
        entry["from"] = peer
    path = log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    if req["kind"] == "ask":
        item = load_answer(req["id"]) or {"id": req["id"]}
        item.update({"status": "answered" if outcome == "received" else outcome, "closed": entry["time"]})
        if answer is not None:
            item.update({"answer": answer, "from": peer})
        write_private(answer_path(req["id"]), json.dumps(item, ensure_ascii=False, indent=2) + "\n")


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


def _stamp(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))


def lan_address(run: Callable = subprocess.run) -> Optional[str]:
    """L'indirizzo IPv4 privato con cui la Deck esce nella rete di casa; None se non è privato."""
    try:
        out = run(["ip", "-j", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5)
        src = json.loads(out.stdout or "[]")[0].get("prefsrc")
        ip = ipaddress.ip_address(src)
    except (OSError, ValueError, IndexError, TypeError, AttributeError, subprocess.SubprocessError):
        return None
    return str(ip) if ip.is_private and not ip.is_loopback else None


# ---- Le pagine

_PAGE = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentDeck: {title}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:34rem;margin:2rem auto;padding:0 1rem;color:#222;
background:#fafafa}}label{{display:block;margin:1rem 0 .3rem;font-weight:600}}input,textarea,select{{width:100%;
box-sizing:border-box;padding:.6rem;font:inherit;border:1px solid #888;border-radius:.4rem;background:#fff;color:#222}}
textarea{{min-height:7rem}}.opt{{display:flex;gap:.5rem;align-items:center;margin:.3rem 0;font-weight:400}}
.opt input{{width:auto}}button{{margin-top:1.2rem;padding:.7rem 1.2rem;font:inherit;border:0;border-radius:.4rem;
background:#1a5fb4;color:#fff}}.q{{white-space:pre-wrap;background:#eee;padding:.8rem;border-radius:.4rem}}
.err{{color:#a51d2d}}.note{{color:#555;font-size:.9rem}}@media(prefers-color-scheme:dark){{body{{background:#1e1e1e;
color:#eee}}input,textarea,select{{background:#2a2a2a;color:#eee}}.q{{background:#2a2a2a}}.note{{color:#aaa}}
.err{{color:#f66}}}}</style></head><body>{body}</body></html>"""


def _input(name: str, label_: str, kind: str, options: Optional[list] = None) -> str:
    common = f'id="{name}" name="{name}" autocomplete="off" autocapitalize="off" spellcheck="false" required'
    head = f'<label for="{name}">{html.escape(label_)}</label>'
    if kind == "textarea":
        return head + f"<textarea {common}></textarea>"
    if kind == "choice":
        return (f"<fieldset style='border:0;padding:0'><legend><b>{html.escape(label_)}</b></legend>"
                + "".join(f'<label class="opt"><input type="radio" name="{name}" value="{html.escape(o)}" required>'
                          f"{html.escape(o)}</label>" for o in options or []) + "</fieldset>")
    return head + f'<input type="{"password" if kind == "password" else "text"}" {common}>'


def form_page(req: dict, error: Optional[str] = None) -> str:
    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    if req["kind"] == "secret":
        name = req["name"]
        title = SLOTS[name]["title"] if name in SLOTS else f"Segreto: {name}"
        fields = "".join(_input(k, lab, kind) for k, lab, kind in secret_fields(name))
        intro = ("<p>AgentDeck chiede questo segreto. Il valore va direttamente nel file della Deck, con permessi "
                 "600: l'agente non lo vede e non passa dalla chat.</p>")
    else:
        title = req["title"]
        fields = "".join(_input(f["name"], f["label"], f["type"], f.get("options")) for f in req["fields"])
        intro = f'<p>L\'agente di AgentDeck ti chiede:</p><p class="q">{html.escape(req["question"])}</p>'
    body = (f"<h1>{html.escape(title)}</h1>{intro}{err}<form method=\"post\">{fields}"
            f'<button type="submit">Invia</button></form>'
            f'<p class="note">La pagina vale una volta sola e si chiude appena rispondi o fra pochi minuti.</p>')
    return _PAGE.format(title=html.escape(title), body=body)


def done_page() -> str:
    return _PAGE.format(title="Ricevuto", body="<h1>Ricevuto</h1><p>Grazie: AgentDeck ha ricevuto la risposta. "
                                               "Puoi chiudere questa pagina, che non vale più.</p>")


def _plain(code_title: str) -> str:
    return _PAGE.format(title="AgentDeck", body=f"<h1>{code_title}</h1>")


# ---- Il server monouso

class _Handler(BaseHTTPRequestHandler):
    server_version = "AgentDeck"
    sys_version = ""
    timeout = 15  # un client che apre la connessione e tace non tiene occupato un thread per sempre
    drop: "Drop"

    def log_message(self, format, *args):  # noqa: A002 - il percorso contiene il token: niente su stderr
        pass

    def _send(self, code: int, page: str) -> None:
        body = page.encode("utf-8")
        self.send_response(code)
        for k, v in (("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body))),
                     ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                     ("X-Frame-Options", "DENY"), ("X-Content-Type-Options", "nosniff"),
                     ("X-Robots-Tag", "noindex"),
                     ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _peer(self) -> str:
        # dietro il tunnel il collegamento viene da cloudflared in locale: l'indirizzo vero lo dice Cloudflare
        forwarded = self.headers.get("CF-Connecting-IP", "")
        try:
            return str(ipaddress.ip_address(forwarded.strip()))
        except ValueError:
            return self.client_address[0]

    def _ours(self) -> bool:
        if secrets.compare_digest(self.path.split("?")[0], "/" + self.drop.req["token"]):
            return True
        with self.drop.lock:
            self.drop.stray += 1
            if self.drop.stray >= MAX_STRAY and self.drop.outcome is None:
                self.drop.outcome = "too_many_attempts"
        self._send(404, _plain("Non trovato"))
        return False

    def do_GET(self):
        if self._ours():
            self._send(200, form_page(self.drop.req))

    def do_POST(self):
        if not self._ours():
            return
        req = self.drop.req
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_BODY:
            self._bad(413, "Risposta troppo lunga.")
            return
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"), max_num_fields=MAX_FIELDS + 4)
        try:
            if req["kind"] == "secret":
                content, answer = secret_content(req["name"], form), None
            else:
                content, answer = None, ask_answer(req["fields"], form)
        except Refused as e:
            self._bad(400, e.message)
            return
        with self.drop.lock:  # due invii validi insieme: vale solo il primo
            if self.drop.outcome is not None:
                self._send(410, _plain("Pagina già usata"))
                return
            if content is not None:
                write_private(slot_path(req["name"]), content)
            self.drop.outcome, self.drop.peer, self.drop.answer = "received", self._peer(), answer
        self._send(200, done_page())

    def _bad(self, code: int, message: str) -> None:
        with self.drop.lock:
            self.drop.bad += 1
            if self.drop.bad >= MAX_BAD and self.drop.outcome is None:
                self.drop.outcome = "too_many_attempts"
        self._send(code, form_page(self.drop.req, message))


class Drop:
    """Un server per una richiesta: si ferma al primo invio valido, alla scadenza o dopo troppi tentativi.

    Un thread per connessione, così le connessioni aperte in anticipo dal browser non bloccano le altre. Con
    via=internet avvia cloudflared come figlio e lo ferma quando finisce: il tunnel vive quanto il server.
    """

    def __init__(self, req: dict, port: Optional[int] = None):
        self.req, self.bad, self.stray = req, 0, 0
        self.outcome: Optional[str] = None
        self.peer: Optional[str] = None
        self.answer: Optional[dict] = None
        self.lock = threading.Lock()
        handler = type("Handler", (_Handler,), {"drop": self})
        self.server = ThreadingHTTPServer((req["host"], req["port"] if port is None else port), handler)
        self.server.daemon_threads = True
        self.server.timeout = 0.5
        self.tunnel: Optional[subprocess.Popen] = None

    @property
    def port(self) -> int:
        return self.server.server_address[1]

    def open_tunnel(self) -> bool:
        """Avvia cloudflared verso questo server e scrive l'indirizzo pubblico nella richiesta appena lo legge."""
        binary = cloudflared()
        if not binary:
            return False
        self.tunnel = subprocess.Popen([binary, "tunnel", "--no-autoupdate", "--url",
                                        f"http://127.0.0.1:{self.port}"],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                       text=True)

        def read(stream):
            found = False
            for line in stream:  # si legge tutto, così cloudflared non si blocca; non si registra niente
                m = _PUBLIC.search(line)
                if m and not found:
                    found = True
                    update_request(public_url=m.group(0))
        threading.Thread(target=read, args=(self.tunnel.stderr,), daemon=True).start()
        return True

    def run(self, now: Callable[[], float] = time.time) -> str:
        try:
            if self.req["via"] == "internet" and not self.open_tunnel():
                self.outcome = "no_tunnel"
            while self.outcome is None and now() < self.req["expires_at"]:
                self.server.handle_request()
        finally:
            self.server.server_close()
            if self.tunnel is not None:
                self.tunnel.terminate()
                try:
                    self.tunnel.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.tunnel.kill()
                    self.tunnel.wait(timeout=10)
                if self.tunnel.stderr is not None:
                    self.tunnel.stderr.close()
        outcome = self.outcome or "expired"
        finish(self.req, outcome, self.peer, self.answer)
        return outcome


def serve() -> int:
    """Avvio dall'unità agentdeck-pagina: legge la richiesta in corso e la serve."""
    req = load_request()
    if req is None:
        return 1
    if time.time() >= req["expires_at"]:
        finish(req, "expired")
        return 0
    Drop(req).run()
    return 0


# ---- Avvio dalla schermata

class LaunchError(Exception):
    """La richiesta non è partita: code è stabile (no_home_network, no_cloudflared, not_started, no_tunnel)."""

    def __init__(self, code: str, output: str = ""):
        super().__init__(code)
        self.code, self.output = code, output


def probe(url: str) -> bool:
    """La pagina risponde da quell'indirizzo? Una GET non consuma la richiesta."""
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


class Launcher:
    """Prepara la richiesta, avvia l'unità a tempo e aspetta che la pagina risponda; chiude quella aperta prima."""

    def __init__(self, sh: Callable = subprocess.run, lan: Callable[[], Optional[str]] = lan_address,
                 check: Callable[[str], bool] = probe, wait_s: float = 5.0, tunnel_wait_s: float = 60.0,
                 has_cloudflared: Callable[[], Optional[str]] = cloudflared):
        self.sh, self.lan, self.check = sh, lan, check
        self.wait_s, self.tunnel_wait_s, self.has_cloudflared = wait_s, tunnel_wait_s, has_cloudflared

    def _cmd(self, argv: list):
        return self.sh(argv, capture_output=True, text=True, timeout=30)

    def running(self) -> bool:
        return self._cmd(["systemctl", "is-active", UNIT]).stdout.strip() in ("active", "activating")

    def _listening(self) -> bool:
        return bool(self._cmd(["ss", "-Hltn", f"sport = :{PORT}"]).stdout.strip())

    def stop(self) -> None:
        self._cmd(["sudo", "-n", "systemctl", "stop", UNIT])
        self._cmd(["sudo", "-n", "systemctl", "reset-failed", UNIT])

    def cancel(self) -> Optional[dict]:
        req = load_request()
        self.stop()
        if req is not None:
            finish(req, "cancelled")
        return req

    def start(self, kind: str, via: str, **spec) -> dict:
        if via == "internet":
            if not self.has_cloudflared():
                raise LaunchError("no_cloudflared")
            host = "127.0.0.1"  # dietro il tunnel la pagina non serve nemmeno in casa
        else:
            host = self.lan()
            if host is None:
                raise LaunchError("no_home_network")
        old = load_request()
        self.stop()  # una richiesta alla volta: la nuova sostituisce quella aperta
        if old is not None:
            finish(old, "replaced")
        req = new_request(kind, via, host, **spec)
        user = pwd.getpwuid(os.getuid()).pw_name
        env = [f"--setenv=HOME={Path.home()}"] + [f"--setenv={k}={os.environ[k]}" for k in
                                                   ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "AGENTDECK_CLOUDFLARED")
                                                   if os.environ.get(k)]
        started = self._cmd(["sudo", "-n", "systemd-run", f"--unit={UNIT}", f"--uid={user}", f"--gid={user}",
                             f"--property=RuntimeMaxSec={TTL_S + 60}", "--collect", "--quiet", *env,
                             sys.executable, str(Path(__file__).resolve())])
        ok = started.returncode == 0
        deadline = time.monotonic() + self.wait_s
        while ok and not (self.running() and self._listening()) and time.monotonic() < deadline:
            time.sleep(0.2)
        if not (ok and self.running() and self._listening()):
            self.stop()
            finish(req, "not_started")
            raise LaunchError("not_started", (started.stderr or started.stdout or "")[-1000:])
        if via == "internet":
            deadline = time.monotonic() + self.tunnel_wait_s
            while time.monotonic() < deadline:
                current = load_request() or {}
                if current.get("public_url") and self.check(link(current)):
                    return current
                time.sleep(1)
            self.stop()
            finish(req, "no_tunnel")
            raise LaunchError("no_tunnel")
        return load_request() or req


if __name__ == "__main__":
    sys.exit(serve())
