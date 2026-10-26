"""Adattatore dei programmi interattivi (O10.T7): un programma gira in tmux e l'agente lo vede come dati.

Quello che un terminale mostra a una persona (righe, cursore, domande, scelte) diventa la schermata di
components/term.py: session, terminal, question, parsed. Qui stanno il backend tmux, la lettura dello stato del
processo e del terminale, il riconoscimento delle domande (regole generiche più i profili per programma) e lo stato
delle sessioni. Documentazione: docs/adattatore.md.

Segnali usati, verificati sulla Deck il 26/10/2026:
- il processo in primo piano che legge dal terminale dorme in wait_woken (/proc/<pid>/wchan); /proc/<pid>/syscall
  non è leggibile (Yama ptrace_scope=1);
- terminale canonico senza eco (icanon -echo) vuol dire una password; senza modo canonico è un programma a tutto
  schermo, che di solito usa anche lo schermo alternativo.
Tutto il testo del terminale è testo esterno: finisce solo nei dati della schermata (INV-4).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional

SOCKET = "agentdeck-term"
PREFIX = "adp-"
COLS, ROWS = 160, 48
MAX_SESSIONS = 8
STALL_S = 30
QUIET_S = 0.5
POLL_S = 0.1
TTY_WAITS = {"wait_woken", "n_tty_read", "do_select", "do_sys_poll", "poll_schedule_timeout", "core_sys_select",
             "ep_poll", "do_epoll_wait"}
TMUX_CONF = ("set -g remain-on-exit on\nset -g remain-on-exit-format ''\nset -g history-limit 5000\n"
             "set -g status off\nset -g escape-time 0\n")
ID = re.compile(r"[0-9a-f]{4}")
PROGRAM = re.compile(r"[a-z0-9][a-z0-9._+-]{0,63}")
QUESTION_TYPES = ("confirm", "choice", "text", "secret", "menu", "pager", "unknown")
KEYS = ("Enter", "Escape", "Tab", "BSpace", "Up", "Down", "Left", "Right", "Space", "PageUp", "PageDown", "Home",
        "End", "C-c", "C-d", "C-z", "C-l", "q", "y", "n")
_WRAPPERS = {"sudo", "doas", "env", "nice", "nohup", "stdbuf", "time", "timeout", "ionice", "chrt", "unbuffer"}
_ARG_OPTS = {"-u", "-g", "-C", "-D", "-p", "-r", "-t", "-U", "-s", "-k", "-c"}  # opzioni degli involucri con argomento


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck" / "term"


def profile_dirs() -> tuple:
    """(profili scritti dall'agente, profili forniti con deck): i primi hanno la precedenza."""
    data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data) / "agentdeck" / "profiles", Path(__file__).resolve().parent.parent / "profiles"


# backend tmux

class Tmux:
    """Le sessioni dell'adattatore, su un server tmux tutto loro (-L agentdeck-term)."""

    def __init__(self):
        self.conf = state_dir() / "tmux.conf"

    def available(self) -> bool:
        try:
            return subprocess.run(["tmux", "-V"], capture_output=True, timeout=5).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _run(self, *args: str, check: bool = True) -> str:
        self.conf.parent.mkdir(parents=True, exist_ok=True)
        if not self.conf.is_file() or self.conf.read_text() != TMUX_CONF:
            self.conf.write_text(TMUX_CONF)
        env = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")}  # anche dentro la sessione claude
        r = subprocess.run(["tmux", "-L", SOCKET, "-f", str(self.conf), *args], capture_output=True, text=True,
                           timeout=10, env=env)
        if check and r.returncode != 0:
            raise RuntimeError(f"tmux {args[0]} failed: {r.stderr.strip()}")
        return r.stdout

    def start(self, name: str, command: str, cwd: str) -> None:
        self._run("new-session", "-d", "-s", name, "-x", str(COLS), "-y", str(ROWS), "-c", cwd, command)

    def names(self) -> list:
        out = self._run("list-sessions", "-F", "#{session_name}", check=False)
        return [n for n in out.split() if n.startswith(PREFIX)]

    def info(self, name: str) -> dict:
        fields = ("pane_pid", "pane_tty", "cursor_x", "cursor_y", "alternate_on", "pane_dead", "pane_dead_status",
                  "pane_dead_signal", "pane_width", "pane_height")
        out = self._run("display-message", "-p", "-t", name, "\x1f".join("#{%s}" % f for f in fields)).rstrip("\n")
        return dict(zip(fields, out.split("\x1f")))

    def visible(self, name: str) -> list:
        return self._run("capture-pane", "-p", "-t", name).split("\n")[:-1]

    def history(self, name: str) -> list:
        return self._run("capture-pane", "-p", "-J", "-t", name, "-S", "-", "-E", "-").split("\n")[:-1]

    def send_text(self, name: str, text: str) -> None:
        self._run("send-keys", "-t", name, "-l", "--", text)

    def send_key(self, name: str, key: str) -> None:
        self._run("send-keys", "-t", name, key)

    def kill(self, name: str) -> None:
        self._run("kill-session", "-t", name, check=False)


def proc_info(pid: int) -> dict:
    """Processo in primo piano sul terminale della sessione: nome e su cosa dorme (Linux, /proc)."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        tpgid = int(stat[stat.rindex(")") + 2:].split()[5])
        fg = tpgid if tpgid > 0 else pid
        return {"pid": fg, "name": Path(f"/proc/{fg}/comm").read_text().strip(),
                "wchan": Path(f"/proc/{fg}/wchan").read_text().strip() or None}
    except (OSError, ValueError, IndexError):
        return {"pid": None, "name": None, "wchan": None}


def tty_flags(tty: str) -> tuple:
    """(eco, modo canonico) del terminale della sessione, o (None, None) se non si legge."""
    try:
        out = subprocess.run(["stty", "-F", tty, "-a"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    words = set(out.replace(";", " ").split())
    echo = True if "echo" in words else False if "-echo" in words else None
    icanon = True if "icanon" in words else False if "-icanon" in words else None
    return echo, icanon


# programmi e profili

def program_of(command: str) -> Optional[str]:
    """Il programma di un comando, saltando assegnazioni di variabili e comandi involucro come sudo."""
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    i, after_wrapper = 0, False
    while i < len(words):
        w = words[i]
        base = os.path.basename(w)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", w) or base in _WRAPPERS or (
                after_wrapper and (w.startswith("-") or re.fullmatch(r"\d+(\.\d+)?[smhd]?", w))):
            after_wrapper = after_wrapper or base in _WRAPPERS
            i += 2 if after_wrapper and w in _ARG_OPTS else 1
            continue
        name = base.lower()
        return name if PROGRAM.fullmatch(name) else None
    return None


def validate_profile(profile) -> list:
    """I problemi di un profilo, vuoto se è valido (formato in docs/adattatore.md)."""
    if not isinstance(profile, dict):
        return ["the profile must be a JSON object"]
    problems = []
    if not isinstance(profile.get("program"), str) or not PROGRAM.fullmatch(profile["program"]):
        problems.append("program must be a lowercase program name")
    unknown = set(profile) - {"program", "description", "author", "questions", "parse"}
    problems += [f"unknown field {k}" for k in sorted(unknown)]
    rules = profile.get("questions", [])
    parse = profile.get("parse", [])
    if not isinstance(rules, list) or not isinstance(parse, list):
        return problems + ["questions and parse must be lists"]
    if len(rules) + len(parse) > 50:
        problems.append("at most 50 rules")
    for i, q in enumerate(rules):
        where = f"questions[{i}]"
        if not isinstance(q, dict):
            problems.append(f"{where} must be an object")
            continue
        problems += [f"{where}.{k} is not a known field" for k in sorted(set(q) - {"id", "pattern", "type", "default",
                                                                                    "options", "options_pattern"})]
        if not isinstance(q.get("id"), str) or not re.fullmatch(r"[a-z0-9_-]{1,32}", q["id"]):
            problems.append(f"{where}.id must be a short lowercase id")
        if q.get("type") not in QUESTION_TYPES:
            problems.append(f"{where}.type must be one of {', '.join(QUESTION_TYPES)}")
        problems += _regex_problems(q.get("pattern"), f"{where}.pattern")
        if "options_pattern" in q:
            problems += _regex_problems(q["options_pattern"], f"{where}.options_pattern", ("key",))
        opts = q.get("options", [])
        if not isinstance(opts, list) or not all(isinstance(o, dict) and isinstance(o.get("key"), str) for o in opts):
            problems.append(f"{where}.options must be a list of objects with a key")
    for i, p in enumerate(parse):
        where = f"parse[{i}]"
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}",
                                                                                              p.get("name", "")):
            problems.append(f"{where} needs a snake_case name")
            continue
        problems += _regex_problems(p.get("pattern"), f"{where}.pattern")
    return problems


def _regex_problems(pattern, where: str, groups: tuple = ()) -> list:
    if not isinstance(pattern, str) or not 0 < len(pattern) <= 300:
        return [f"{where} must be a regular expression of 1 to 300 characters"]
    try:
        rx = re.compile(pattern, re.MULTILINE)
    except re.error as e:
        return [f"{where} is not a valid regular expression ({e.msg})"]
    return [f"{where} needs the named group {g}" for g in groups if g not in rx.groupindex]


def load_profile(program: Optional[str]) -> tuple:
    """(profilo, origine "agent" o "builtin") per il programma, oppure (None, None)."""
    if not program or not PROGRAM.fullmatch(program):
        return None, None
    for directory, origin in zip(profile_dirs(), ("agent", "builtin")):
        path = directory / f"{program}.json"
        try:
            profile = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not validate_profile(profile):
            return profile, origin
    return None, None


def list_profiles() -> list:
    found: dict = {}
    for directory, origin in reversed(list(zip(profile_dirs(), ("agent", "builtin")))):
        for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
            if PROGRAM.fullmatch(path.stem):
                found[path.stem] = origin
    return [{"program": p, "origin": o} for p, o in sorted(found.items())]


def save_profile(profile: dict) -> Path:
    path = profile_dirs()[0] / f"{profile['program']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)
    return path


# riconoscimento delle domande

_CONFIRM = re.compile(r"[\[(]\s*(?P<y>y(?:es)?)\s*/\s*(?P<n>no?)\b[^\n]{0,30}?[\])]\s*[:?]?\s*$", re.IGNORECASE)
_DEFAULT = re.compile(r"default\s*[=:]?\s*(?P<d>\w+)|\[(?P<b>\d+)\]", re.IGNORECASE)
_NUMBERED = re.compile(r"(?:^|\s)(?P<key>\d{1,3})[).]\s+(?P<label>\S(?:.*?\S)?)(?=\s{2,}\d{1,3}[).]\s|\s*$)")
_SECRET_WORDS = re.compile(r"(pass(word|phrase|code)?|pin|token|secret)\b[^:\n]*:\s*$", re.IGNORECASE)
_PAGER = re.compile(r"\(END\)\s*$|--More--|^:\s*$|^\s*lines \d+-\d+", re.IGNORECASE)
_PROMPT_END = re.compile(r"[:?>#$]\s*$")


def _nonblank_tail(lines: list, upto: int, count: int = 8) -> list:
    tail = [ln for ln in lines[:upto + 1] if ln.strip()]
    return tail[-count:]


def recognize(lines: list, cursor: tuple, *, echo: Optional[bool], icanon: Optional[bool], alternate: bool,
              waiting: bool, profile: Optional[dict] = None) -> Optional[dict]:
    """La domanda che il programma sta facendo, o None se non ne fa. Il testo resta testo esterno: solo dati."""
    cx, cy = cursor
    cy = min(max(cy, 0), max(len(lines) - 1, 0))
    prompt = lines[cy][:cx] if lines else ""
    tail = _nonblank_tail(lines, cy)

    if profile:
        found = _profile_question(profile, tail)
        if found:
            return found
    if not waiting:
        return None
    if echo is False and icanon is True:
        return _question(prompt or (tail[-1] if tail else ""), "secret", "generic:echo-off")
    bottom = next((ln for ln in reversed(lines) if ln.strip()), "")
    if (alternate or icanon is False) and _PAGER.search(bottom):
        return _question(bottom, "pager", "generic:pager",
                         options=[{"key": "space", "label": "next page"}, {"key": "q", "label": "quit"}])
    if alternate:
        return _question(bottom, "unknown", "generic:fullscreen")
    # modo a righe: canonico, oppure un editor di riga come readline (bash interattiva), che spegne eco e icanon
    if not prompt.strip():
        return _question(tail[-1] if tail else "", "unknown", "generic:no-prompt")
    if _SECRET_WORDS.search(prompt):
        return _question(prompt, "secret", "generic:secret-word")
    m = _CONFIRM.search(prompt)
    if m:
        long_form = len(m.group("y")) > 1
        default = None
        if m.group("y")[0].isupper() != m.group("n")[0].isupper():
            default = ("yes" if long_form else "y") if m.group("y")[0].isupper() else ("no" if long_form else "n")
        return _question(prompt, "confirm", "generic:yes-no", default=default,
                         options=[{"key": "yes" if long_form else "y", "label": "yes"},
                                  {"key": "no" if long_form else "n", "label": "no"}])
    options = []
    for ln in tail[:-1] if len(tail) > 1 else []:
        options += [{"key": o.group("key"), "label": o.group("label")} for o in _NUMBERED.finditer(ln)]
    if options and _PROMPT_END.search(prompt):
        d = _DEFAULT.search(prompt)
        default = (d.group("d") or d.group("b")) if d else None
        return _question(prompt, "choice", "generic:numbered", options=_unique(options), default=default)
    if _PROMPT_END.search(prompt):
        return _question(prompt, "text", "generic:prompt")
    return _question(prompt, "unknown", "generic:waiting")


def _profile_question(profile: dict, tail: list) -> Optional[dict]:
    """La prima regola che riconosce la domanda in corso: la corrispondenza deve finire sulla riga del cursore,
    così una domanda già risposta, ancora visibile sopra, non vince su quella nuova (visto con ssh-keygen)."""
    text = "\n".join(tail)
    for rule in profile.get("questions", []):
        m = next((m for m in re.finditer(rule["pattern"], text, re.MULTILINE)
                  if text.count("\n", 0, m.end()) == len(tail) - 1), None)
        if not m:
            continue
        first = text.count("\n", 0, m.start())
        last = text.count("\n", 0, m.end())
        question_text = "\n".join(tail[first:last + 1])
        options = [dict(o) for o in rule.get("options", [])]
        if "options_pattern" in rule:
            options += [{"key": o.group("key"), "label": (o.groupdict().get("label") or o.group("key"))}
                        for o in re.finditer(rule["options_pattern"], text, re.MULTILINE)]
        default = m.groupdict().get("default") or rule.get("default")
        return _question(question_text, rule["type"], f"profile:{profile['program']}#{rule['id']}",
                         options=_unique(options), default=default,
                         fields={k: v for k, v in m.groupdict().items() if k != "default" and v is not None})
    return None


def parse_screen(profile: Optional[dict], lines: list) -> dict:
    """I dati che il profilo estrae dallo schermo (regole parse)."""
    parsed: dict = {}
    if not profile:
        return parsed
    text = "\n".join(lines)
    for rule in profile.get("parse", []):
        matches = list(re.finditer(rule["pattern"], text, re.MULTILINE))
        if not matches:
            continue
        values = [m.groupdict() or {"match": m.group(0)} for m in matches]
        parsed[rule["name"]] = values if rule.get("all") else values[-1]
    return parsed


def _unique(options: list) -> list:
    seen, out = set(), []
    for o in options:
        if o["key"] not in seen:
            seen.add(o["key"])
            out.append(o)
    return out


def _question(text: str, type_: str, origin: str, *, options: Optional[list] = None, default=None,
              fields: Optional[dict] = None) -> dict:
    q = {"text": text.strip(), "type": type_, "options": options or [], "default": default, "origin": origin}
    if fields:
        q["fields"] = fields
    return q


# sessioni

class Sessions:
    """Sessioni dell'adattatore: tmux per il programma, un file di stato per ciò che l'agente ha già visto."""

    def __init__(self, backend=None, clock=time.time, sleep=time.sleep, proc=proc_info, flags=tty_flags):
        self.tmux = backend or Tmux()
        self.clock, self.sleep, self.proc, self.flags = clock, sleep, proc, flags

    def _state_path(self, sid: str) -> Path:
        return state_dir() / f"{sid}.json"

    def _state(self, sid: str) -> dict:
        try:
            return json.loads(self._state_path(sid).read_text())
        except (OSError, ValueError):
            return {"id": sid}

    def _save(self, state: dict) -> None:
        path = self._state_path(state["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        tmp.replace(path)

    def ids(self) -> list:
        return sorted(n[len(PREFIX):] for n in self.tmux.names() if ID.fullmatch(n[len(PREFIX):]))

    def exists(self, sid: str) -> bool:
        return sid in self.ids()

    def start(self, command: str, cwd: str) -> str:
        used = set(self.ids())
        sid = secrets.token_hex(2)
        while sid in used:
            sid = secrets.token_hex(2)
        self.tmux.start(PREFIX + sid, command, cwd)
        now = self.clock()
        self._save({"id": sid, "command": command, "program": program_of(command), "cwd": cwd, "started": now,
                    "seen": 0, "hash": None, "changed": now})
        return sid

    def observe(self, sid: str, *, mark_seen: bool = True) -> dict:
        """Lo stato della sessione adesso, come dati della schermata."""
        name = PREFIX + sid
        state = self._state(sid)
        info = self.tmux.info(name)
        lines = self.tmux.visible(name)
        history = self.tmux.history(name)
        while lines and not lines[-1].strip():
            lines.pop()
        while history and not history[-1].strip():
            history.pop()
        dead = info.get("pane_dead") == "1"
        cursor = (_int(info.get("cursor_x")), _int(info.get("cursor_y")))
        now = self.clock()
        digest = hashlib.sha256(("\n".join(lines) + f"|{cursor}|{dead}").encode()).hexdigest()
        if digest != state.get("hash"):
            state["hash"], state["changed"] = digest, now
        idle = now - state.get("changed", now)
        fg = {"pid": None, "name": None, "wchan": None} if dead else self.proc(_int(info.get("pane_pid")))
        echo, icanon = (None, None) if dead else self.flags(info.get("pane_tty") or "")
        alternate = info.get("alternate_on") == "1"
        tty_wait = (fg.get("wchan") or "").split(".")[0] in TTY_WAITS  # il kernel aggiunge .constprop.0, .isra.0
        profile, profile_origin = load_profile(state.get("program"))
        quiet = idle >= QUIET_S
        question = None if dead else recognize(lines, cursor, echo=echo, icanon=icanon, alternate=alternate,
                                                 waiting=tty_wait and quiet, profile=profile if quiet else None)
        if dead:
            status = "exited"
        elif question is not None and quiet:
            status = "waiting_input"
        elif not tty_wait and idle >= STALL_S:
            status = "stalled"
        else:
            status = "running"
        seen = state.get("seen", 0)
        new_lines = history[seen:] if seen <= len(history) else lines
        if mark_seen:
            state["seen"] = len(history)
        self._save(state)
        return {
            "session": {"id": sid, "command": state.get("command"), "program": state.get("program"),
                        "state": status, "exit_status": _int(info.get("pane_dead_status")) if dead else None,
                        "exit_signal": _int(info.get("pane_dead_signal")) if dead and info.get("pane_dead_signal")
                        else None,
                        "started": _iso(state.get("started")), "duration_s": int(now - state.get("started", now)),
                        "idle_s": int(idle), "foreground": {"pid": fg.get("pid"), "name": fg.get("name"),
                                                            "waiting_on": fg.get("wchan")},
                        "alternate_screen": alternate},
            "terminal": {"cols": _int(info.get("pane_width")) or COLS, "rows": _int(info.get("pane_height")) or ROWS,
                         "cursor": {"x": cursor[0], "y": cursor[1]}, "echo": echo, "canonical": icanon,
                         "lines": lines, "new_lines": new_lines[-200:]},
            "question": question,
            "parsed": parse_screen(profile, history[-400:]) if profile else {},
            "profile": {"program": profile["program"], "origin": profile_origin} if profile else None,
        }

    def settle(self, sid: str, max_s: float) -> dict:
        """Aspetta che il programma chieda qualcosa, esca o resti fermo; al più max_s secondi."""
        deadline = self.clock() + max_s
        while True:
            data = self.observe(sid, mark_seen=False)
            st = data["session"]["state"]
            if st in ("exited", "waiting_input", "stalled") or self.clock() >= deadline:
                return self.observe(sid)
            self.sleep(POLL_S)

    def send_text(self, sid: str, text: str, enter: bool) -> None:
        self.tmux.send_text(PREFIX + sid, text)
        if enter:
            self.tmux.send_key(PREFIX + sid, "Enter")
        self._touch(sid)

    def send_key(self, sid: str, key: str, repeat: int = 1) -> None:
        for _ in range(repeat):
            self.tmux.send_key(PREFIX + sid, key)
        self._touch(sid)

    def _touch(self, sid: str) -> None:
        state = self._state(sid)
        state["hash"], state["changed"] = None, self.clock()
        self._save(state)

    def close(self, sid: str) -> None:
        self.tmux.kill(PREFIX + sid)
        try:
            self._state_path(sid).unlink()
        except OSError:
            pass


def _int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iso(ts) -> Optional[str]:
    if ts is None:
        return None
    from datetime import datetime
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")
