#!/usr/bin/env python3
"""Hook PreToolUse di Claude Code sulla Deck: protegge l'accesso (INV-1) e i servizi e le credenziali dell'utente (ADR-0001).

Claude Code passa su stdin un JSON con tool_name e tool_input; uscire con 2 blocca il comando e il testo su stderr
torna all'agente. È il secondo strato dopo le regole deny delle impostazioni gestite: guarda anche dentro sudo,
catene di comandi e varianti che un prefisso non coglie. In dubbio lascia passare: è una guardia, non un sandbox.
Se il comando passa e deck copre la stessa cosa, aggiunge al contesto l'azione di deck da preferire, senza bloccare
(politica sui comandi grezzi, O10.T8); per i programmi che fanno domande indica l'adattatore, deck term.
Versioni fisse (O18.T3): le installazioni senza versione fuori da pacman (agentdeck/pinning.py) si rifiutano, salvo il
consenso motivato AGENTDECK_LATEST_OK="<motivo>" nel comando, registrato in ~/.local/state/agentdeck/latest-consents.jsonl.
Permessi (ADR-0001, O12.T1): AgentDeck è dell'agente, che lavora sul sistema senza chiedere; quando uno strumento tocca
un servizio o una credenziale dell'utente (agentdeck/ownership.py) l'hook risponde permissionDecision "deny" con il
motivo, e l'agente prosegue con altro. Mai "ask": dal 29/10/2026 (decisione dell'utente, piano punto 8) nessuna
richiesta arriva a un umano come domanda che ferma la sessione; deciderà l'arbitro agentico (O19.T3). Vale per Bash,
per le modifiche di file e per gli strumenti MCP di deck.
Installato da deck/install.sh in /opt/agentdeck/claude. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # /opt/agentdeck o deck/ del repository

from agentdeck.access import RULES, check  # noqa: E402,F401  le regole stanno con deck: le usa anche deck term
from agentdeck import ownership, pinning, term  # noqa: E402
from agentdeck.system import deck_state_dir  # noqa: E402

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
PINNING = ("AgentDeck guard: refused because this installs software without a fixed version ({reason}). Since O18.T3 "
           "every install outside pacman names its version (npm i pkg@1.2.3, pip install pkg==1.2.3, cargo install "
           "crate@1.2.3, image:tag, `deck claude/version switch` for Claude Code). If a fixed version is not possible "
           "or this is a false positive, repeat the command with the prefix AGENTDECK_LATEST_OK=\"<why, at least 10 "
           "characters>\": the consent is recorded.")
CONSENTED = ("AgentDeck: install without a fixed version allowed by your recorded consent (AGENTDECK_LATEST_OK). "
             "Note in your report which version got installed.")
ASK = ("AgentDeck: not done, because {reason}: that belongs to the owner (ADR-0001). The owner is never asked through a "
       "permission prompt that stops the session (owner decision of 29/10/2026). Do not wait: go on with the rest of "
       "your work, and list this in your report so the owner can decide. If it is only a reading, rewrite it without "
       "writes or redirections to files.")


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
    consented = None
    if tool == "Bash":
        reason = check(command)
        if reason is not None:
            print(MESSAGE.format(reason=reason), file=sys.stderr)
            return 2
        unpinned = pinning.check(command)
        if unpinned is not None:
            why = pinning.consent(command)
            if why is None:
                print(PINNING.format(reason=unpinned), file=sys.stderr)
                return 2
            pinning.record(deck_state_dir() / "latest-consents.jsonl", command, why, unpinned,
                           str(event.get("session_id") or "") or None)
            consented = CONSENTED
    owner = ownership.tool_reason(tool, tool_input)
    if owner:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": ASK.format(reason=owner)}}))
        return 0
    if tool != "Bash":
        return 0
    text = " ".join(x for x in (consented, hint(command)) if x)
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
