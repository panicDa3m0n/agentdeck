#!/usr/bin/env python3
"""Hook SessionStart di Claude Code sulla Deck: all'inizio di ogni sessione il sistema dice all'agente com'è la Deck.

È l'autoprompting all'ingresso: host, versione, tempo di attività, gli avvisi di `deck status` ognuno con l'azione
di deck che lo gestisce, gli obblighi aperti del sistema (O10.T8) e come è finita la sessione precedente, dal
registro delle sessioni. Si usano solo i campi scritti dal sistema (codici e messaggi di avvisi e obblighi,
indirizzi delle azioni, nomi di strumenti): nessun testo esterno entra nel contesto (INV-4). Ciò che mostra viene
segnato come già visto, così l'hook di ogni turno (turn.py) porta solo le novità. Se deck non risponde, lo dice.
Installato da deck/install.sh in /opt/agentdeck/claude. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import sys
from typing import Optional

import hooklib


def context(home, status, obligations: Optional[list] = None, last: Optional[dict] = None) -> str:
    if not home or not status:
        return ("AgentDeck session start: `deck` did not answer, so the state of the Deck is unknown. Run `deck status` "
                "first and fix deck before anything else.")
    meta = home.get("data") or {}
    lines = [f"AgentDeck session start. Host {meta.get('host')}, deck {meta.get('version')}, "
             f"up {int(meta.get('uptime_s') or 0) // 60} minutes."]
    alerts = status.get("alerts") or []
    if alerts:
        lines.append(f"{len(alerts)} alerts from `deck status`:")
        lines += [hooklib.alert_line(a) for a in alerts]
    else:
        lines.append("No alerts from `deck status`.")
    if obligations:
        lines.append(f"{len(obligations)} open obligations from the system (they only warn, for now):")
        lines += [hooklib.obligation_line(o) for o in obligations]
    if last:
        lines.append(previous(last))
    lines.append("Components: " + ", ".join(f"`deck {c['path'].lstrip('/')}`" for c in (home.get("nav") or {}).get(
        "children", [])) + ". The same screens are MCP tools: mcp__deck__open and mcp__deck__<component>_<action>. "
        "Start from the alerts and obligations, if any; otherwise wait for the owner's request.")
    return "\n".join(lines)


def previous(last: dict) -> str:
    reason = last.get("reason") if last.get("reason") in hooklib.END_REASONS else "other"
    tools = [f"{n} x{c}" for n, c in (last.get("tools") or {}).items()
             if isinstance(n, str) and hooklib.NAME.fullmatch(n) and isinstance(c, int)][:6]
    ended = last.get("ended") if isinstance(last.get("ended"), str) and hooklib.ISO.fullmatch(last["ended"]) else None
    calls = last.get("tool_calls") if isinstance(last.get("tool_calls"), int) else 0
    text = f"Previous session ended {ended or 'at an unknown time'} ({reason}), {calls} tool calls"
    return text + (f"; most used: {', '.join(tools)}." if tools else ".")


def main() -> int:
    event = hooklib.read_event()
    home, status = hooklib.screen("/"), hooklib.screen("/status")
    opened = hooklib.open_obligations()
    hooklib.emit("SessionStart", context(home, status, opened, hooklib.last_session()))
    hooklib.save_state(event.get("session_id"), {"alerts": [a.get("code") for a in (status or {}).get("alerts", [])],
                                                 "obligations": [o["id"] for o in opened]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
