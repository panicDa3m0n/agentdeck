"""Riga di comando di deck: legge la chiamata, produce una schermata JSON, imposta il codice di uscita.

Uso: deck [indirizzo] [azione] [nome=valore ...] [--pretty]
     deck mcp   (le stesse schermate come server MCP su stdio: agentdeck/mcp.py)
Specifica: docs/protocollo.md (sezione 2). Documentazione: docs/deck.md.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import obligations, version
from .components import all_components
from .engine import Deck, DeckError, call_tokens
from .protocol import sys_text, validate


def render(deck: Deck, argv: list) -> tuple:
    """Esegue una chiamata e restituisce (schermata, codice di uscita). Non scrive nulla."""
    started = time.monotonic()
    args = [a for a in argv if a != "--pretty"]
    if args in (["--help"], ["-h"]):
        args = ["/protocol"] if "/protocol" in deck.components else ["/"]
    try:
        path, action_id, raw, extra = call_tokens(args)
        if extra:
            raise DeckError("BAD_PARAM", sys_text("Too many words: the call is `{cmd} [path] [action] "
                                                  "[name=value ...]`.", cmd=deck.command),
                            title=sys_text("Invalid call"), children=deck.home_children(),
                            prompt=sys_text("Pass parameters as name=value. Run `deck /protocol` to see how "
                                            "calls are built."))
        result = deck.handle(path, action_id, raw)
    except DeckError as e:
        result = deck.error_screen(e)
    except Exception as e:  # un guasto interno resta comunque una schermata valida
        result = deck.failed_screen(e)

    # i doveri aperti viaggiano con ogni schermata di deck (protocollo, 6 bis); quelle di brain non li portano
    if deck.obligations and result.get("path") != "/obligations":
        pending = obligations.for_screen()
        if pending:
            result["obligations"] = pending
    result["meta"] = _meta(started)
    problems = validate(json.loads(json.dumps(result)))
    if problems:
        result = deck.failed_screen(RuntimeError("screen does not follow the protocol"),
                                    {"protocol_problems": problems})
        result["meta"] = _meta(started)
    return result, 1 if result["status"] == "error" else 0


def _meta(started: float) -> dict:
    return {"time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "took_ms": int((time.monotonic() - started) * 1000),
            "host": socket.gethostname(), "version": version()}


def call_summary(result: dict, argv: list, command: str = "deck") -> str:
    """Esito di una chiamata per lo schermo della Deck: "indirizzo|azione|stato|codice|avvisi".

    Per un comando diverso da deck (brain) l'indirizzo porta davanti il nome del comando: "brain /memory".
    """
    _, action_id, _, _ = call_tokens([a for a in argv if a != "--pretty"])
    code = (result.get("error") or {}).get("code", "")
    where = result["path"] if command == "deck" else f"{command} {result['path']}"
    fields = [where, action_id or "", result["status"], code, str(len(result.get("alerts", [])))]
    return "|".join(f.replace("|", "/") for f in fields)


def log_call(result: dict, argv: list, command: str = "deck") -> None:
    """Scrive l'esito della chiamata nel journal, per lo schermo della Deck (docs/schermo.md).

    Solo sulla Deck, dove esiste il journal, e mai durante i test (AGENTDECK_NO_LOG).
    """
    if os.environ.get("AGENTDECK_NO_LOG") or not Path("/run/systemd/journal/socket").exists():
        return
    try:
        import syslog
        syslog.openlog("agentdeck")
        syslog.syslog(call_summary(result, argv, command))
    except Exception:  # lo schermo è un di più: un problema di registro non deve toccare la risposta
        pass


def main(argv: Optional[list] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["mcp"]:  # server MCP su stdio (docs/deck.md, "Server MCP"): mcp non è un indirizzo
        from .mcp import serve
        return serve()
    if argv == ["ui"]:  # server della pagina dello schermo (docs/interfacce.md): ui non è un indirizzo
        from .ui import serve as serve_ui
        return serve_ui()
    return run(Deck(all_components()), argv)


def run(deck: Deck, argv: list) -> int:
    """Una chiamata da riga di comando: stampa la schermata e la registra per lo schermo. La usa anche brain."""
    result, code = render(deck, argv)
    if "--pretty" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    log_call(result, argv, deck.command)
    return code
