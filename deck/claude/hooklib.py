"""Parti comuni agli hook di AgentDeck per Claude Code (O10.T8): deck importato, stato per sessione, uscita JSON.

Gli hook leggono deck importandolo, non con un comando: le loro letture non finiscono sullo schermo della Deck. Nel
contesto dell'agente mettono solo testo del sistema (INV-4): codici e messaggi di avvisi e obblighi, indirizzi e
nomi di azioni, identificatori validati. Lo stato per sessione (cosa l'agente ha già ricevuto) sta in
$XDG_STATE_HOME/agentdeck/claude/<session_id>.json; il registro delle sessioni in .../agentdeck/sessions.jsonl.
Documentazione: docs/claude-code.md, "Autoprompting: gli hook".
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # /opt/agentdeck o deck/ del repository

from agentdeck import cli, obligations  # noqa: E402
from agentdeck.components import all_components  # noqa: E402
from agentdeck.engine import Deck  # noqa: E402

SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,80}")
NAME = re.compile(r"[A-Za-z0-9@._-]{1,64}")
ISO = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d")
END_REASONS = ("clear", "resume", "logout", "prompt_input_exit", "bypass_permissions_disabled", "other")


def read_event() -> dict:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return {}
    return event if isinstance(event, dict) else {}


def screen(path: str) -> Optional[dict]:
    """Una schermata di deck, in forma JSON, o None se deck non risponde."""
    try:
        result, _ = cli.render(Deck(all_components()), [path])
        return json.loads(json.dumps(result))
    except Exception:
        return None


def open_obligations() -> list:
    try:
        return [o for o in obligations.for_screen() if o["id"] != "more"]
    except Exception:
        return []


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck"


def _session_file(session_id) -> Optional[Path]:
    if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
        return None
    return state_dir() / "claude" / f"{session_id}.json"


def load_state(session_id) -> dict:
    path = _session_file(session_id)
    try:
        state = json.loads(path.read_text()) if path else {}
    except (OSError, ValueError):
        state = {}
    return {"alerts": list(state.get("alerts", [])), "obligations": list(state.get("obligations", []))}


def save_state(session_id, state: dict) -> None:
    path = _session_file(session_id)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
    except OSError:
        pass


def emit(event_name: str, text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}))


def action_hint(target) -> str:
    if not isinstance(target, dict) or not target.get("path"):
        return ""
    return f" (handle with `deck {target['path'].lstrip('/')} {target.get('action') or ''}`)".replace(" `)", "`)")


def alert_line(a: dict) -> str:
    return f"- [{a.get('level')}] {a.get('code')}: {a.get('message')}{action_hint(a.get('action'))}"


def obligation_line(o: dict) -> str:
    return f"- [{o.get('level')}] {o.get('code')} {o.get('id')}: {o.get('message')}"


def last_session() -> Optional[dict]:
    try:
        lines = (state_dir() / "sessions.jsonl").read_text().splitlines()
        return json.loads(lines[-1]) if lines else None
    except (OSError, ValueError, IndexError):
        return None
