#!/usr/bin/env python3
"""Schermo della Deck: mostra in tempo reale, come un terminale, i comandi dell'agente, la loro risposta
e l'esito di deck.

Segue il journal (agentdeck-cmd, agentdeck-out e agentdeck-err scritti da ssh-log.sh; agentdeck scritto da
deck) e stampa sul terminale di tty1. È un canale verso l'umano: testi in italiano; caratteri di controllo ripuliti
e valori che sembrano segreti oscurati.
Avviato dal servizio agentdeck-screen.service. Documentazione: docs/schermo.md
"""
from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from typing import Optional

RESET, DIM, BOLD = "\x1b[0m", "\x1b[2m", "\x1b[1m"
GREEN, YELLOW, RED, CYAN = "\x1b[32m", "\x1b[33m", "\x1b[31m", "\x1b[36m"

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_SECRET = re.compile(r"(?i)\b(pass(?:word)?|passwd|token|secret|api[_-]?key|authorization)(\s*[=:]\s*|\s+)(\S+)")
_BEARER = re.compile(r"(?i)\b(bearer|basic)(\s+)(\S+)")
_TRANSFER = ("/usr/lib/ssh/sftp-server", "scp ", "rsync --server")


def clean(text: str) -> str:
    """Testo sicuro da stampare: niente sequenze di controllo, segreti oscurati."""
    text = _CONTROL.sub("?", text)
    hide = lambda m: m.group(1) + m.group(2) + "***"  # noqa: E731
    return _SECRET.sub(hide, _BEARER.sub(hide, text))


def shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: max(limit - 1, 1)] + "…"


def describe_command(message: str) -> str:
    first, _, rest = message.partition("\n")
    if first.startswith(_TRANSFER):
        return "(trasferimento di file)"
    return first + (" …" if rest.strip() else "")


def describe_deck(message: str) -> Optional[tuple]:
    """Esito di deck: il messaggio è "indirizzo|azione|stato|codice|avvisi"."""
    parts = message.split("|")
    if len(parts) != 5:
        return None
    path, action, status, code, alerts = parts
    where = path + (" " + action if action else "")
    if status == "error":
        return RED, f"{where}: errore {code}"
    if status == "confirm":
        return YELLOW, f"{where}: anteprima, in attesa di conferma"
    if status == "done":
        return GREEN, f"{where}: eseguito"
    return GREEN, f"{where}: ok" + (f", {alerts} avvisi" if alerts not in ("", "0") else "")


MAX_ROWS_PER_LINE = 3


def wrap(text: str, width: int, max_rows: int = MAX_ROWS_PER_LINE) -> list:
    """Spezza una riga lunga in righe di schermo, al massimo max_rows; l'ultima finisce con … se taglia."""
    width = max(width, 10)
    rows = [text[i:i + width] for i in range(0, len(text), width)] or [""]
    if len(rows) > max_rows:
        rows = rows[:max_rows]
        rows[-1] = rows[-1][: width - 1] + "…"
    return rows


def format_output(ident: str, message: str, when: str, width: int) -> Optional[str]:
    """Una riga della risposta di un comando, sotto il comando stesso; gli errori in rosso."""
    text = clean(message).rstrip()
    if not text.strip() or text.startswith('{"deck":'):  # la risposta di deck è già nella riga "→ deck"
        return None
    indent = " " * (len(when) + 1)
    color, reset = (RED, RESET) if ident == "agentdeck-err" else ("", "")
    return "\n".join(f"{indent}{color}{row}{reset}" for row in wrap(text, width - len(indent) - 1))


def format_entry(entry: dict, width: int) -> Optional[str]:
    message = entry.get("MESSAGE")
    if not isinstance(message, str):
        return None
    try:
        when = datetime.fromtimestamp(int(entry["__REALTIME_TIMESTAMP"]) / 1e6).strftime("%H:%M:%S")
    except (KeyError, ValueError):
        when = "--:--:--"
    ident = entry.get("SYSLOG_IDENTIFIER")
    if ident in ("agentdeck-out", "agentdeck-err"):
        return format_output(ident, message, when, width)
    if ident == "agentdeck-cmd":
        prompt = "agent@agentdeck:~$ "
        command = shorten(clean(describe_command(message)), width - len(when) - len(prompt) - 2)
        return f"{DIM}{when}{RESET} {GREEN}{BOLD}agent@agentdeck{RESET}:{CYAN}~{RESET}$ {command}"
    if ident == "agentdeck":
        described = describe_deck(message)
        if described is None:
            return None
        color, text = described
        return f"{DIM}{when}{RESET}   {color}→ deck {shorten(clean(text), width - len(when) - 12)}{RESET}"
    return None


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # nessun pacchetto inviato: serve solo a scegliere l'interfaccia
            return s.getsockname()[0]
    except OSError:
        return "?"


def banner(width: int) -> str:
    title = f" AgentDeck · {socket.gethostname()} · {local_ip()} "
    line = "─" * max(width - 1, 10)
    return (f"\x1b[2J\x1b[H{CYAN}{line}{RESET}\n{BOLD}{title}{RESET}\n"
            f"{DIM} Attività dell'agente: i comandi compaiono qui mentre vengono eseguiti.{RESET}\n"
            f"{CYAN}{line}{RESET}\n")


def main() -> int:
    width = shutil.get_terminal_size((106, 33)).columns
    sys.stdout.write("\x1b[?25l" + banner(width))  # cursore nascosto
    sys.stdout.flush()
    follow = subprocess.Popen(["journalctl", "-f", "-n", "25", "-o", "json", "-t", "agentdeck-cmd", "-t", "agentdeck",
                               "-t", "agentdeck-out", "-t", "agentdeck-err"], stdout=subprocess.PIPE, text=True)
    assert follow.stdout is not None
    for line in follow.stdout:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        out = format_entry(entry, width)
        if out:
            print(out, flush=True)
    return follow.wait()


if __name__ == "__main__":
    sys.exit(main())
