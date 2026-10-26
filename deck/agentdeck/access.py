"""Regole che proteggono l'accesso dell'agente alla Deck (INV-1): i comandi che lo toglierebbero.

Le usano la guardia di Claude Code sui comandi Bash (claude/guard.py) e l'adattatore dei programmi interattivi
(components/term.py), che non fa partire né digita in una shell un comando che le viola. Sono una guardia, non un
sandbox: in dubbio lasciano passare, e il resto lo proteggono deck service e deck network.
Documentazione: docs/claude-code.md (guardia) e docs/adattatore.md.
"""
from __future__ import annotations

import re
from typing import Optional

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


def check(command: str) -> Optional[str]:
    """Il motivo del rifiuto, o None se il comando può passare."""
    for reason, pattern in RULES:
        if pattern.search(command):
            return reason
    return None
