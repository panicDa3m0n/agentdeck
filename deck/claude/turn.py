#!/usr/bin/env python3
"""Hook UserPromptSubmit di Claude Code sulla Deck: a ogni turno il sistema porta all'agente solo le novità.

Confronta gli avvisi di `deck status` e gli obblighi aperti con quelli che la sessione ha già ricevuto (stato per
sessione di hooklib, scritto anche da session_start.py): avvisi nuovi o rientrati, obblighi nuovi o chiusi. Se non
è cambiato niente non scrive niente, così il contesto non si riempie di ripetizioni. Solo testo del sistema (INV-4).
Installato da deck/install.sh in /opt/agentdeck/claude. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import sys

import hooklib


def delta(state: dict, alerts: list, opened: list) -> tuple:
    """(righe da dire all'agente, nuovo stato) confrontando ciò che c'è ora con ciò che la sessione ha già visto."""
    codes = [a.get("code") for a in alerts]
    ids = [o["id"] for o in opened]
    lines = [hooklib.alert_line(a) for a in alerts if a.get("code") not in state["alerts"]]
    lines += [f"- alert {c} cleared" for c in state["alerts"] if c not in codes and hooklib.NAME.fullmatch(str(c))]
    lines += [hooklib.obligation_line(o) for o in opened if o["id"] not in state["obligations"]]
    lines += [f"- obligation {i} closed" for i in state["obligations"] if i not in ids and hooklib.NAME.fullmatch(str(i))]
    return lines, {"alerts": codes, "obligations": ids}


def main() -> int:
    event = hooklib.read_event()
    sid = event.get("session_id")
    status = hooklib.screen("/status")
    if status is None:
        return 0
    lines, state = delta(hooklib.load_state(sid), status.get("alerts") or [], hooklib.open_obligations())
    hooklib.save_state(sid, state)
    if lines:
        hooklib.emit("UserPromptSubmit", "AgentDeck, changes since your last turn:\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
