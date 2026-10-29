"""Ciò che appartiene all'utente (ADR-0001): l'agente chiede il permesso solo per questo, per il resto di AgentDeck no.

Decisione dell'utente del 26/10/2026. AgentDeck è il sistema di proprietà e uso completo dell'agente; i permessi
riguardano solo:
- i servizi dell'utente, in /srv/servizi/<nome>: codice, configurazione, dati e segreti, e le unità
  agentdeck-servizio@<nome> (avvio, arresto, riavvio, abilitazione);
- le credenziali dell'utente: il login di Claude, le chiavi SSH e il login di GitHub (gh, ADR-0002), che l'agente usa
  per pubblicare ma non legge né copia.
I progetti che l'utente chiede all'agente (per esempio /home/agent/frugale) non sono in questo elenco: lì l'agente
lavora libero. Leggere non è intervenire: elenchi, letture e stato restano liberi, tranne il contenuto delle credenziali.

Lo usa l'hook PreToolUse di Claude Code (claude/guard.py), che in questi casi non procede e lo dice all'agente
(deny con il motivo, mai una domanda che ferma la sessione: decisione del 29/10/2026). Il corpo degli heredoc non si
analizza: è testo passato a un programma.
È un confine di proprietà, non un sandbox: in dubbio lascia passare. I vincoli che proteggono l'accesso stanno in
access.py. Documentazione: docs/claude-code.md, "Permessi (ADR-0001)".
"""
from __future__ import annotations

import re
import shlex
from typing import Optional

from . import pinning

SERVICE_NAME = r"[a-z][a-z0-9-]{0,27}"
SERVICE_DIR = re.compile(rf"/srv/servizi/({SERVICE_NAME})(?![a-z0-9-])")
SERVICE_UNIT = re.compile(rf"\bagentdeck-servizio@({SERVICE_NAME})(?![a-z0-9-])")
CREDENTIALS = re.compile(r"(?:/home/agent|~|\$HOME)/(?:\.claude/\.credentials\.json|\.ssh/|\.config/gh/)|^\.ssh/|"
                         r"\.claude/\.credentials\.json|\.config/gh/hosts\.yml")
TOKEN_COMMANDS = re.compile(r"\bgh\s+auth\s+(?:token|status\b[^;&|\n]*--show-token|refresh|logout)|\bgh\s+auth\s+login\b")
UNIT_VERBS = re.compile(r"\b(?:start|stop|restart|try-restart|reload|reload-or-restart|enable|disable|mask|unmask|kill|edit|"
                        r"revert|set-property)\b")
READ_ONLY = {"ls", "cat", "head", "tail", "less", "more", "stat", "file", "wc", "grep", "rg", "find", "du", "diff", "cmp",
             "sha256sum", "md5sum", "tree", "readlink", "realpath", "journalctl", "echo", "printf", "true", "test", "[",
             "cd", "pwd", "pushd", "popd", "jq", "sort", "uniq", "cut", "nl", "column", "basename", "dirname"}
READ_ONLY_GIT = re.compile(r"\bgit\b(?:\s+-C\s+\S+)?\s+(?:log|status|diff|show|blame|branch|remote|rev-parse|ls-files)\b")
# reindirizzamenti che non scrivono file: verso /dev/null o fra canali (O19.T1, falso positivo del 29/10)
HARMLESS_REDIRECT = re.compile(r"(?:\d|&)?>{1,2}\s*/dev/null|\d?>&\d|<\s*/dev/null")
SERVICE_SECRETS = re.compile(r"/srv/servizi/[a-z][a-z0-9-]*/(?:[^\s;&|]*/)?(?:\.?secrets?\b|[^\s;&|]*\.key\b|config/env\b)")
READ_ONLY_SYSTEMCTL = re.compile(r"\bsystemctl\b[^;&|\n]*\b(?:status|show|is-active|is-enabled|is-failed|cat|list-units|"
                                 r"list-unit-files|list-dependencies)\b")
SECRET_READERS = {"cat", "head", "tail", "less", "more", "grep", "rg", "cp", "scp", "base64", "xxd", "od"}
WRITE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
SERVICE_ACTIONS = ("start", "stop", "restart", "enable", "disable")


def _segments(command: str) -> list:
    """I comandi semplici di una riga: separati da ;, &&, ||, | e a capo."""
    return [s.strip() for s in re.split(r"\|\||&&|[;|\n]", command) if s.strip()]


def _program(segment: str) -> str:
    try:
        words = shlex.split(segment)
    except ValueError:
        words = segment.split()
    words = [w for w in words if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", w)]
    while words and words[0] in ("sudo", "env", "nice", "nohup", "time", "command"):
        words = words[1:]
        while words and words[0].startswith("-"):
            words = words[1:]
    return words[0].rsplit("/", 1)[-1] if words else ""


def _reads_only(segment: str) -> bool:
    segment = HARMLESS_REDIRECT.sub(" ", segment)
    if re.search(r">|\btee\b|-delete\b|-exec\b|\bsed\s+-i\b", segment):
        return False
    if READ_ONLY_SYSTEMCTL.search(segment) or READ_ONLY_GIT.search(segment):
        return True
    return _program(segment) in READ_ONLY


def _service(text: str) -> Optional[str]:
    m = SERVICE_DIR.search(text) or SERVICE_UNIT.search(text)
    return m.group(1) if m else None


def command_reason(command: str) -> Optional[str]:
    """Perché un comando Bash interviene su qualcosa dell'utente, o None se è lavoro di sistema libero."""
    inside = None  # il servizio in cui un cd ha portato la catena: i comandi dopo lavorano lì
    for segment in _segments(pinning.strip_heredocs(command)):  # il corpo di un heredoc è testo, non comandi
        if TOKEN_COMMANDS.search(segment):
            return "it reads or changes the owner's credentials (GitHub login)"
        if CREDENTIALS.search(segment) and (not _reads_only(segment) or _program(segment) in SECRET_READERS):
            return "it touches the owner's credentials (Claude login, SSH keys or GitHub login)"
        name = _service(segment)
        if _program(segment) in ("cd", "pushd"):
            inside = name
            continue
        if name is None:
            if inside and _program(segment) != "deck" and not _reads_only(segment):
                return f"it changes files of the owner's service {inside}"
            continue
        if SERVICE_UNIT.search(segment) and re.search(r"\bsystemctl\b", segment) and UNIT_VERBS.search(segment):
            return f"it starts, stops or changes the owner's service {name}"
        if re.search(r"\bdeck\b[^;&|\n]*\bservice\s+(?:start|stop|restart|enable|disable)\b", segment):
            return f"it starts, stops or changes the owner's service {name}"
        if _program(segment) == "deck":
            continue  # le altre chiamate a deck leggono, e deck protegge da sé le sue azioni
        if SERVICE_SECRETS.search(segment) and _program(segment) in SECRET_READERS:
            return f"it reads the secrets of the owner's service {name}"
        if not _reads_only(segment):
            return f"it changes files of the owner's service {name}"
    return None


def path_reason(path: str) -> Optional[str]:
    if CREDENTIALS.search(path):
        return "it writes the owner's credentials (Claude login, SSH keys or GitHub login)"
    name = _service(path)
    return f"it changes files of the owner's service {name}" if name else None


def tool_reason(tool_name: str, tool_input: dict) -> Optional[str]:
    """Perché questo uso di uno strumento di Claude Code va chiesto all'utente (ADR-0001), o None."""
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Bash":
        return command_reason(str(tool_input.get("command", "")))
    if tool_name in WRITE_TOOLS:
        return path_reason(str(tool_input.get("file_path") or tool_input.get("notebook_path") or ""))
    if tool_name.startswith("mcp__deck__service_") and tool_name.rsplit("_", 1)[-1] in SERVICE_ACTIONS:
        name = _service(str(tool_input.get("name", "")))
        return f"it starts, stops or changes the owner's service {name}" if name else None
    if tool_name in ("mcp__deck__term_start", "mcp__deck__term_answer"):
        return command_reason(str(tool_input.get("command") or tool_input.get("text") or ""))
    return None
