#!/usr/bin/env python3
"""Hook SessionEnd di Claude Code sulla Deck: il registro delle sessioni (A5.6, O10.T8).

Alla fine di una sessione conta gli strumenti usati, dalla trascrizione che Claude Code indica in transcript_path, e
scrive una riga in $XDG_STATE_HOME/agentdeck/sessions.jsonl (le ultime 100) e nel journal, con identificatore
agentdeck-session. La sessione successiva la riceve da session_start.py: il sistema ricorda per l'agente, che non ha
memoria. Si registrano solo nomi di strumenti, conteggi, date e il motivo della fine, mai testo della conversazione.
Installato da deck/install.sh in /opt/agentdeck/claude. Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import hooklib

KEEP = 100


def count_tools(transcript: str) -> Counter:
    counts: Counter = Counter()
    try:
        lines = Path(transcript).read_text(errors="replace").splitlines()
    except (OSError, TypeError):
        return counts
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if entry.get("type") != "assistant" or not isinstance(content, list):
            continue
        for block in content:
            name = block.get("name") if isinstance(block, dict) and block.get("type") == "tool_use" else None
            if isinstance(name, str) and hooklib.NAME.fullmatch(name):
                counts[name] += 1
    return counts


def record(event: dict) -> dict:
    counts = count_tools(event.get("transcript_path"))
    sid = event.get("session_id")
    return {
        "session_id": sid if isinstance(sid, str) and hooklib.SESSION_ID.fullmatch(sid) else None,
        "ended": datetime.now().astimezone().isoformat(timespec="seconds"),
        "reason": event.get("reason") if event.get("reason") in hooklib.END_REASONS else "other",
        "tool_calls": sum(counts.values()),
        "tools": dict(counts.most_common(15)),
        "obligations_open": len(hooklib.open_obligations()),
    }


def main() -> int:
    entry = record(hooklib.read_event())
    path = hooklib.state_dir() / "sessions.jsonl"
    try:
        old = path.read_text().splitlines()[-(KEEP - 1):] if path.exists() else []
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(old + [json.dumps(entry)]) + "\n")
    except OSError:
        pass
    if os.environ.get("AGENTDECK_NO_LOG"):  # nei test non si scrive nel registro di sistema
        return 0
    try:
        import syslog
        syslog.openlog("agentdeck-session")
        syslog.syslog(json.dumps(entry, separators=(",", ":")))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
