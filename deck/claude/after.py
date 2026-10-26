#!/usr/bin/env python3
"""Hook PostToolUse di Claude Code sulla Deck: dopo un comando Bash o la modifica di un file, il sistema dice cosa
verificare e porta gli obblighi nati da quell'azione (O10.T8).

- pacman che installa: l'hook di pacman ha registrato un obbligo per i programmi senza profilo; verificare;
- pacman che rimuove, systemctl che cambia un servizio, scritture in /etc: le verifiche da fare con deck;
- obblighi aperti che la sessione non ha ancora ricevuto.
Gli strumenti MCP di deck non passano di qui: le loro schermate portano già prompt e obblighi.
Solo testo del sistema (INV-4): dal comando dell'agente entrano al più nomi di unità validati.
Installato da deck/install.sh in /opt/agentdeck/claude. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import re
import sys

import hooklib

PACMAN_INSTALL = re.compile(r"\bpacman\b[^;&|\n]*\s-(?:S(?![a-z]*[sicgl])[a-z]*|U[a-z]*)\b")
PACMAN_REMOVE = re.compile(r"\bpacman\b[^;&|\n]*\s-R[a-z]*\b")
SYSTEMCTL = re.compile(r"\bsystemctl\b[^;&|\n]*?\b(start|stop|restart|reload|enable|disable|mask|unmask|edit)\b"
                       r"(?:\s+--\S+)*\s+([A-Za-z0-9@._-]+)")
DAEMON_RELOAD = re.compile(r"\bsystemctl\b[^;&|\n]*\bdaemon-reload\b")
ETC_WRITE = re.compile(r"(?:\bsed\s+-i\b|\btee\b|>{1,2}|\b(?:cp|mv|install|ln|rm|chmod|chown)\b)[^;&|\n]*\s/etc/")

ETC_HINT = ("A file in /etc changed: make sure a snapshot covers the change (`deck snapshot`), verify the service "
            "that reads the file with `deck service show name=<unit>`, and say in your report what changed and why.")


def hints(tool: str, tool_input: dict) -> list:
    found = []
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        if command.lstrip().startswith("deck "):
            return []
        if PACMAN_INSTALL.search(command):
            found.append("Packages were installed: the pacman hook records an obligation for new programs without an "
                         "adapter profile, listed below if any; `deck obligations` has them all. Check `deck status` "
                         "for alerts.")
        elif PACMAN_REMOVE.search(command):
            found.append("Packages were removed: check `deck status` for failed services and the snapshot pair snap-pac "
                         "took (`deck snapshot`).")
        m = SYSTEMCTL.search(command)
        if m:
            unit = m.group(2) if hooklib.NAME.fullmatch(m.group(2)) else "<unit>"
            found.append(f"A service changed ({m.group(1)}): verify it with `deck service show name={unit}` and read its "
                         f"logs with `deck logs query unit={unit} since=5m`.")
        elif DAEMON_RELOAD.search(command):
            found.append("systemd reloaded its units: check `deck service` for failed services.")
        if ETC_WRITE.search(command):
            found.append(ETC_HINT)
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if path.startswith("/etc/"):
            found.append(ETC_HINT)
    return found


def main() -> int:
    event = hooklib.read_event()
    sid = event.get("session_id")
    lines = hints(str(event.get("tool_name", "")), event.get("tool_input") or {})
    state = hooklib.load_state(sid)
    opened = hooklib.open_obligations()
    new = [o for o in opened if o["id"] not in state["obligations"]]
    if new:
        lines.append("New obligations from the system:")
        lines += [hooklib.obligation_line(o) for o in new]
        state["obligations"] = [o["id"] for o in opened]
        hooklib.save_state(sid, state)
    if lines:
        hooklib.emit("PostToolUse", "AgentDeck: " + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
