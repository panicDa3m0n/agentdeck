#!/usr/bin/env python3
"""Hook PreToolUse di Claude Code sulla Deck: protegge l'accesso (INV-1) e i servizi e le credenziali dell'utente (ADR-0001).

Claude Code passa su stdin un JSON con tool_name e tool_input; uscire con 2 blocca il comando e il testo su stderr
torna all'agente. È il secondo strato dopo le regole deny delle impostazioni gestite: guarda anche dentro sudo,
catene di comandi e varianti che un prefisso non coglie. In dubbio lascia passare: è una guardia, non un sandbox.
Se il comando passa e deck copre la stessa cosa, aggiunge al contesto l'azione di deck da preferire, senza bloccare
(politica sui comandi grezzi, O10.T8); per i programmi che fanno domande indica l'adattatore, deck term.
Permessi (ADR-0001, O12.T1): AgentDeck è dell'agente, che lavora sul sistema senza chiedere; quando uno strumento tocca
un servizio o una credenziale dell'utente (agentdeck/ownership.py) l'hook risponde permissionDecision "ask" e Claude Code
chiede all'utente. Vale per Bash, per le modifiche di file e per gli strumenti MCP di deck.
Installato da deck/install.sh in /opt/agentdeck/claude. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # /opt/agentdeck o deck/ del repository

from agentdeck.access import RULES, check  # noqa: E402,F401  le regole stanno con deck: le usa anche deck term
from agentdeck import ownership, term  # noqa: E402

HINTS = [
    (re.compile(r"\bjournalctl\b"), "`deck logs query` (unit=, since=, priority=, lines=) returns journal lines as data"),
    (re.compile(r"\bsnapper\b"), "`deck snapshot` lists, creates and rolls back snapshots, with a preview"),
    (re.compile(r"\bpacman\b[^;&|\n]*\s-S[a-z]*u|\bcheckupdates\b"),
     "`deck update` checks and applies updates with snapshots before and after and a verification"),
    (re.compile(r"\bsystemctl\b[^;&|\n]*\b(?:start|stop|restart|enable|disable)\b"),
     "`deck service <action> name=<unit>` previews the change, protects access and verifies the result"),
    (re.compile(r"\bsystemctl\b[^;&|\n]*\b(?:status|list-units|list-unit-files|show|is-active|is-enabled)\b"),
     "`deck service` and `deck service show name=<unit>` give the same facts as data"),
    (re.compile(r"\b(?:iwctl|nmcli|resolvectl|iw\s+dev|ip\s+(?:a|addr|link|route|r))\b"),
     "`deck network` shows interfaces, Wi-Fi, name resolution and ports, and changes them safely"),
]
INTERACTIVE = re.compile(r"\bpacman\b[^;&|\n]*\s-[SRU](?![a-z]*[sicglp])(?![^;&|\n]*--noconfirm)|\bread\s+-p\b")

MESSAGE = ("AgentDeck guard: refused because this command could cut the agent's access to the Deck ({reason}, "
           "INV-1). This is a limit of the system, not a permission to ask for. Use deck instead: `deck service` and "
           "`deck network` preview the change and protect access; if they do not cover it, make the change with a "
           "safety net that reverts by itself.")
ASK = ("AgentDeck: this needs the owner's permission because {reason}. Under ADR-0001 the agent works on AgentDeck "
       "without asking, and asks only for the owner's services and credentials.")


def hint(command: str):
    """Il suggerimento di deck per un comando che passa, o None. Solo testo scritto qui (INV-4)."""
    if command.lstrip().startswith("deck "):
        return None
    found = [text for pattern, text in HINTS if pattern.search(command)]
    program = term.program_of(command)
    # pacman ha un profilo ma chiede solo con certe operazioni: per lui decide INTERACTIVE
    interactive = bool(INTERACTIVE.search(command)) or (
        program not in (None, "pacman") and term.load_profile(program)[0] is not None)
    if not found and not interactive:
        return None
    parts = []
    if found:
        parts.append("AgentDeck: deck covers this command: " + "; ".join(found) + ". Prefer it, through the MCP tools "
                     "mcp__deck__<component>_<action>.")
    if interactive:
        parts.append("AgentDeck: this program asks questions. Run it with `deck term start command=...` "
                     "(mcp__deck__term_start) to read them as data and answer them deliberately.")
    return " ".join(parts) + " The command runs anyway."


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    command = str(tool_input.get("command", "")) if tool == "Bash" else ""
    if tool == "Bash":
        reason = check(command)
        if reason is not None:
            print(MESSAGE.format(reason=reason), file=sys.stderr)
            return 2
    owner = ownership.tool_reason(tool, tool_input)
    if owner:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": ASK.format(reason=owner)}}))
        return 0
    if tool != "Bash":
        return 0
    text = hint(command)
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
