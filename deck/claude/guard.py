#!/usr/bin/env python3
"""Hook PreToolUse di Claude Code sulla Deck: rifiuta i comandi Bash che toglierebbero l'accesso all'agente (INV-1).

Claude Code passa su stdin un JSON con tool_name e tool_input; uscire con 2 blocca il comando e il testo su stderr
torna all'agente. È il secondo strato dopo le regole deny delle impostazioni gestite: guarda anche dentro sudo,
catene di comandi e varianti che un prefisso non coglie. In dubbio lascia passare: è una guardia, non un sandbox.
Installato da deck/claude/install.sh. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # /opt/agentdeck o deck/ del repository

from agentdeck.access import RULES, check  # noqa: E402,F401  le regole stanno con deck: le usa anche deck term

MESSAGE = ("AgentDeck guard: refused because this command could cut the agent's access to the Deck ({reason}, "
           "INV-1). Use deck instead: `deck service` and `deck network` preview the change and protect access. If "
           "the change is really needed, explain it to the owner and ask first.")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    reason = check(str((event.get("tool_input") or {}).get("command", "")))
    if reason is None:
        return 0
    print(MESSAGE.format(reason=reason), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
