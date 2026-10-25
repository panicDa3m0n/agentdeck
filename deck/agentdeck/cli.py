"""Riga di comando di deck: legge la chiamata, produce una schermata JSON, imposta il codice di uscita.

Uso: deck [indirizzo] [azione] [nome=valore ...] [--pretty]
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

from . import version
from .components import all_components
from .engine import Deck, DeckError, call_tokens
from .protocol import sys_text, validate


def render(deck: Deck, argv: list) -> tuple:
    """Esegue una chiamata e restituisce (schermata, codice di uscita). Non scrive nulla."""
    started = time.monotonic()
    args = [a for a in argv if a != "--pretty"]
    if args in (["--help"], ["-h"]):
        args = ["/protocol"]
    try:
        path, action_id, raw, extra = call_tokens(args)
        if extra:
            raise DeckError("BAD_PARAM", sys_text("Too many words: the call is `deck [path] [action] "
                                                  "[name=value ...]`."),
                            title=sys_text("Invalid call"), children=deck.home_children(),
                            prompt=sys_text("Pass parameters as name=value. Run `deck /protocol` to see how "
                                            "calls are built."))
        result = deck.handle(path, action_id, raw)
    except DeckError as e:
        result = deck.error_screen(e)
    except Exception as e:  # un guasto interno resta comunque una schermata valida
        result = deck.failed_screen(e)

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


def call_summary(result: dict, argv: list) -> str:
    """Esito di una chiamata per lo schermo della Deck: "indirizzo|azione|stato|codice|avvisi"."""
    _, action_id, _, _ = call_tokens([a for a in argv if a != "--pretty"])
    code = (result.get("error") or {}).get("code", "")
    fields = [result["path"], action_id or "", result["status"], code, str(len(result.get("alerts", [])))]
    return "|".join(f.replace("|", "/") for f in fields)


def log_call(result: dict, argv: list) -> None:
    """Scrive l'esito della chiamata nel journal, per lo schermo della Deck (docs/schermo.md).

    Solo sulla Deck, dove esiste il journal, e mai durante i test (AGENTDECK_NO_LOG).
    """
    if os.environ.get("AGENTDECK_NO_LOG") or not Path("/run/systemd/journal/socket").exists():
        return
    try:
        import syslog
        syslog.openlog("agentdeck")
        syslog.syslog(call_summary(result, argv))
    except Exception:  # lo schermo è un di più: un problema di registro non deve toccare la risposta
        pass


def main(argv: Optional[list] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    result, code = render(Deck(all_components()), argv)
    if "--pretty" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    log_call(result, argv)
    return code
