"""Riga di comando di deck: legge la chiamata, produce una schermata JSON, imposta il codice di uscita.

Uso: deck [indirizzo] [azione] [nome=valore ...] [--pretty]
Specifica: docs/protocollo.md (sezione 2). Documentazione: docs/deck.md.
"""
from __future__ import annotations

import json
import socket
import sys
import time
from datetime import datetime
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


def main(argv: Optional[list] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    result, code = render(Deck(all_components()), argv)
    if "--pretty" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return code
