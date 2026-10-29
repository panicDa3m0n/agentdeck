"""Origine di una memoria: la sessione di Claude Code e il messaggio in cui nasce (O22.T1).

La sessione viene da CLAUDE_CODE_SESSION_ID, che Claude Code passa ai comandi e ai server MCP che lancia; il
messaggio è l'ultima richiesta vera (non un risultato di strumento) nella trascrizione della sessione,
~/.claude/projects/<cartella>/<sessione>.jsonl. Così una memoria rimanda al punto in cui è nata. Si legge solo
uuid e forma delle righe: il testo della trascrizione non serve e non esce da qui. Documentazione: docs/brain.md.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .memory import ORIGIN_ID

CHUNK = 1 << 20
MAX_READ = 64 << 20


def projects_dir() -> Path:
    return Path(os.environ.get("AGENTDECK_CLAUDE_PROJECTS") or Path.home() / ".claude" / "projects")


def session_id() -> Optional[str]:
    value = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    return value if ORIGIN_ID.fullmatch(value) else None


def transcript(session: str) -> Optional[Path]:
    try:
        return next(iter(sorted(projects_dir().glob(f"*/{session}.jsonl"))), None)
    except OSError:
        return None


def _is_prompt(line: bytes) -> Optional[str]:
    """L'uuid della riga se è una richiesta dell'utente (testo, non risultato di strumento né messaggio meta)."""
    if b'"type":"user"' not in line:
        return None
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    if not isinstance(entry, dict) or entry.get("type") != "user" or entry.get("isMeta"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        kinds = {b.get("type") for b in content if isinstance(b, dict)}
        if "tool_result" in kinds or "text" not in kinds:
            return None
    elif not isinstance(content, str):
        return None
    uid = entry.get("uuid")
    return uid if isinstance(uid, str) and ORIGIN_ID.fullmatch(uid) else None


def last_prompt(path: Path) -> Optional[str]:
    """L'ultima richiesta nella trascrizione, leggendo dalla fine a blocchi (al massimo MAX_READ byte)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            pos, tail, read = end, b"", 0
            while pos > 0 and read < MAX_READ:
                step = min(CHUNK, pos)
                pos -= step
                f.seek(pos)
                block = f.read(step) + tail
                read += step
                lines = block.split(b"\n")
                tail = lines[0] if pos > 0 else b""  # la prima riga del blocco può essere a metà
                for line in reversed(lines[1:] if pos > 0 else lines):
                    found = _is_prompt(line)
                    if found:
                        return found
    except OSError:
        return None
    return None


def current() -> dict:
    """{"session": ..., "message": ...} della sessione che chiama; None dove non si sa."""
    session = session_id()
    if session is None:
        return {"session": None, "message": None}
    path = transcript(session)
    return {"session": session, "message": last_prompt(path) if path else None}
