#!/usr/bin/env python3
"""Hook PreToolUse di Claude Code sulla Deck: rifiuta i comandi Bash che toglierebbero l'accesso all'agente (INV-1).

Claude Code passa su stdin un JSON con tool_name e tool_input; uscire con 2 blocca il comando e il testo su stderr
torna all'agente. È il secondo strato dopo le regole deny delle impostazioni gestite: guarda anche dentro sudo,
catene di comandi e varianti che un prefisso non coglie. In dubbio lascia passare: è una guardia, non un sandbox.
Installato da deck/claude/install.sh. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import re
import sys

ACCESS_UNITS = r"(?:sshd|systemd-networkd|iwd|systemd-resolved|dbus(?:-broker)?)(?:\.service|\.socket)?"
RULES = [
    ("systemctl stop, disable, mask or kill of an access service",
     re.compile(rf"\bsystemctl\b[^;&|\n]*\b(?:stop|disable|mask|kill|try-restart|isolate)\b[^;&|\n]*\b{ACCESS_UNITS}\b")),
    ("isolating a rescue or emergency target",
     re.compile(r"\bsystemctl\b[^;&|\n]*\b(?:isolate|rescue|emergency)\b[^;&|\n]*\b(?:rescue|emergency)(?:\.target)?\b")),
    ("killing sshd, iwd, networkd or resolved",
     re.compile(r"\b(?:pkill|killall)\b[^;&|\n]*\b(?:sshd|iwd|systemd-networkd|systemd-resolved)\b")),
    ("taking the Wi-Fi or network link down",
     re.compile(r"\b(?:ip\s+link\s+set\s+\S+\s+down|ifconfig\s+\S+\s+down|rfkill\s+block|iwctl\b[^;&|\n]*\bdisconnect\b)")),
    ("editing the SSH server configuration directly",
     re.compile(r"(?:\bsed\s+-i\b|\btee\b|>{1,2})[^;&|\n]*/etc/ssh/sshd_config")),
    ("guard test marker", re.compile(r"agentdeck-guard-canary")),
]
MESSAGE = ("AgentDeck guard: refused because this command could cut the agent's access to the Deck ({reason}, "
           "INV-1). Use deck instead: `deck service` and `deck network` preview the change and protect access. If "
           "the change is really needed, explain it to the owner and ask first.")


def check(command: str):
    """Il motivo del rifiuto, o None se il comando può passare."""
    for reason, pattern in RULES:
        if pattern.search(command):
            return reason
    return None


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
