#!/usr/bin/env python3
"""Hook PermissionRequest di Claude Code sulla Deck: nessuna richiesta di permesso arriva mai a un umano.

Scatta quando Claude Code sta per mostrare una richiesta di permesso, per qualsiasi motivo (sue protezioni interne,
percorsi, strumenti nuovi). Decisione dell'utente del 29/10/2026 (piano punto 8): le richieste non fermano mai la
sessione e non vanno all'umano come domanda. Finché non c'è l'arbitro agentico (O19.T3) la richiesta si approva e si
registra in ~/.local/state/agentdeck/permission-requests.jsonl; i limiti veri restano prima, nelle regole deny e nella
guardia (claude/guard.py), che decidono in PreToolUse e non arrivano qui. Il contenuto della richiesta è testo
esterno: va solo nel registro, mai nel contesto (INV-4).
Installato in /opt/agentdeck/claude. Documentazione: docs/claude-code.md, "Nessuna richiesta all'umano".
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def log_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck" / "permission-requests.jsonl"


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    entry = {"time": datetime.now().astimezone().isoformat(timespec="seconds"),
             "session": event.get("session_id"), "tool": event.get("tool_name"),
             "input": json.dumps(event.get("tool_input"), ensure_ascii=False)[:2000] if event.get("tool_input") else None,
             "suggestions": json.dumps(event.get("permission_suggestions"), ensure_ascii=False)[:1000]
             if event.get("permission_suggestions") else None,
             "decision": "allow"}
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                                             "decision": {"behavior": "allow"}}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
