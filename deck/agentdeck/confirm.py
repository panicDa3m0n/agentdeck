"""Codici di conferma per le azioni distruttive (protocollo, sezione 7).

Specifica: docs/protocollo.md. Documentazione del motore: docs/deck.md.

Un codice vale per una sola azione, con quei parametri, per TTL_S secondi e una volta sola. I codici in
sospeso stanno in $XDG_STATE_HOME/agentdeck/confirm.json (di norma ~/.local/state/agentdeck/).
"""
from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

TTL_S = 300


def _store() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck" / "confirm.json"


def _key(path: str, action: str, params: dict) -> str:
    return json.dumps([path, action, sorted(params.items())], separators=(",", ":"))


def _load(now: float) -> list:
    try:
        items = json.loads(_store().read_text())
    except (FileNotFoundError, ValueError):
        return []
    return [i for i in items if isinstance(i, dict) and i.get("expires_at", 0) > now]


def _save(items: list) -> None:
    store = _store()
    store.parent.mkdir(parents=True, exist_ok=True)
    tmp = store.with_suffix(".tmp")
    tmp.write_text(json.dumps(items))
    os.chmod(tmp, 0o600)
    tmp.replace(store)


def issue(path: str, action: str, params: dict) -> tuple:
    """Crea un codice per questa azione con questi parametri. Restituisce (codice, scadenza ISO 8601)."""
    now = time.time()
    items = _load(now)
    used = {i["token"] for i in items}
    token = secrets.token_hex(2)
    while token in used:
        token = secrets.token_hex(2)
    expires_at = now + TTL_S
    items.append({"token": token, "key": _key(path, action, params), "expires_at": expires_at})
    _save(items)
    return token, datetime.fromtimestamp(expires_at).astimezone().isoformat(timespec="seconds")


def consume(token: str, path: str, action: str, params: dict) -> bool:
    """Vero se il codice è valido per questa azione con questi parametri; in quel caso lo consuma."""
    now = time.time()
    items = _load(now)
    key = _key(path, action, params)
    match = next((i for i in items if i["token"] == token and i["key"] == key), None)
    if match is not None:
        items.remove(match)
    _save(items)
    return match is not None
