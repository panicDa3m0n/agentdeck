#!/usr/bin/env python3
"""Hook SessionStart di Claude Code sulla Deck: all'inizio di ogni sessione il sistema dice all'agente com'è la Deck.

È l'autoprompting all'ingresso: host, versione, tempo di attività e gli avvisi di `deck status`, ognuno con
l'azione di deck che lo gestisce. Si usano solo i campi scritti dal sistema (codici e messaggi degli avvisi,
indirizzi delle azioni): nessun testo esterno entra nel contesto (INV-4). Se deck non risponde, lo dice e basta.
Installato da deck/claude/install.sh. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import subprocess
import sys

DECK = "/usr/local/bin/deck"


def deck(*args: str):
    try:
        out = subprocess.run([DECK, *args], capture_output=True, text=True, timeout=20).stdout
        return json.loads(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def context(home, status) -> str:
    if not home or not status:
        return ("AgentDeck session start: `deck` did not answer, so the state of the Deck is unknown. Run `deck status` "
                "first and fix deck before anything else.")
    meta = home.get("data") or {}
    lines = [f"AgentDeck session start. Host {meta.get('host')}, deck {meta.get('version')}, "
             f"up {int(meta.get('uptime_s') or 0) // 60} minutes."]
    alerts = status.get("alerts") or []
    if alerts:
        lines.append(f"{len(alerts)} alerts from `deck status`:")
        for a in alerts:
            target = a.get("action") or {}
            how = f" (handle with `deck {target.get('path', '').lstrip('/')} {target.get('action') or ''}`)".rstrip() \
                if target.get("path") else ""
            lines.append(f"- [{a.get('level')}] {a.get('code')}: {a.get('message')}{how}")
    else:
        lines.append("No alerts from `deck status`.")
    lines.append("Components: " + ", ".join(f"`deck {c['path'].lstrip('/')}`" for c in (home.get("nav") or {}).get(
        "children", [])) + ". Start from the alerts, if any; otherwise wait for the owner's request.")
    return "\n".join(lines)


def main() -> int:
    text = context(deck(), deck("status"))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
