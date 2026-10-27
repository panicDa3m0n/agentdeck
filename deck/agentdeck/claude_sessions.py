"""Le sessioni Claude della Deck (O15.T2): elencarle, aprirne una nuova, chiuderne una.

Fatti verificati sulla Deck il 27/10/2026, con Claude Code 2.1.310:
- ogni sessione è un processo con una scheda in ~/.claude/sessions/<pid>.json, scritta da Claude Code: titolo (name),
  stato (busy, idle), cartella, id della trascrizione (sessionId), id per l'app (bridgeSessionId, il link
  https://claude.ai/code/<id>) e istante di avvio del processo (procStart, il campo 22 di /proc/<pid>/stat);
- Remote Control accetta un solo server per cartella, e ~/agentdeck ha già il suo (servizio agentdeck-claude). Una
  sessione nuova parte quindi in una sottocartella sua, ~/agentdeck/sessioni/<nome>, con un server che tiene una
  sola sessione ed esce quando lei finisce (--spawn session). La fiducia nella cartella viene da ~/agentdeck;
- SIGINT al processo della sessione la chiude in modo pulito, anche dentro il server con più sessioni, che resta
  pronto; SIGTERM la chiude come errore, e serve solo se SIGINT non basta;
- una sessione appena aperta cambia processo: la prima nasce senza bridgeSessionId e dopo una trentina di secondi
  il server la sostituisce con un processo nuovo, registrato nell'app, con un altro sessionId. Per questo open aspetta
  la registrazione, e l'id delle sessioni aperte da deck viene dalla loro cartella, che non cambia (trappola P24).
Un processo si riconosce dal PID e dal suo istante di avvio: un PID riusato da un altro processo non è la sessione.
Titoli e messaggi dei programmi sono testo esterno: stanno solo nei dati (INV-4).
Schermata: components/claude.py. Documentazione: docs/interfacce.md, docs/claude-code.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

HOME = Path.home()
REGISTRY = HOME / ".claude" / "sessions"
OPENED = HOME / "agentdeck" / "sessioni"
CLAUDE = HOME / ".local" / "bin" / "claude"
PROC = Path("/proc")
TMUX_PREFIX = "rc-"
NAME = re.compile(r"[a-z][a-z0-9-]{0,23}")
ID = re.compile(r"[0-9a-f]{8}")
BRIDGE = re.compile(r"session_[A-Za-z0-9]{10,64}")
STATES = ("busy", "idle")  # appena aperta la scheda non ha ancora lo stato: starting
MAX_OPENED = 8
OPEN_WAIT_S = 45
CLOSE_WAIT_S = 10
FAILED_PANE_S = 60  # se il server non parte, la finestra resta per leggere l'errore


class SessionError(Exception):
    def __init__(self, code: str, detail: Optional[dict] = None):
        super().__init__(code)
        self.code, self.detail = code, detail or {}


def _iso(ms) -> Optional[str]:
    if not isinstance(ms, (int, float)):
        return None
    return datetime.fromtimestamp(ms / 1000).astimezone().isoformat(timespec="seconds")


def _run(argv: list) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "TMUX"}  # deck può girare dentro la tmux del server
    return subprocess.run(argv, capture_output=True, text=True, timeout=15, env=env)


class Sessions:
    """Le sessioni dal registro di Claude Code, verificate sui processi vivi."""

    def __init__(self, registry: Path = REGISTRY, proc: Path = PROC, opened: Path = OPENED, claude: Path = CLAUDE,
                 run=_run, kill=os.kill, clock=time.time, sleep=time.sleep, me=os.getpid):
        self.registry, self.proc, self.opened, self.claude = registry, proc, opened, claude
        self.run, self.kill, self.clock, self.sleep, self.me = run, kill, clock, sleep, me

    # ---- Processi

    def _stat(self, pid: int) -> Optional[list]:
        try:
            stat = (self.proc / str(pid) / "stat").read_text()
            return stat[stat.rindex(")") + 2:].split()
        except (OSError, ValueError):
            return None

    def _alive(self, pid: int, proc_start: str) -> bool:
        fields = self._stat(pid)
        return bool(fields) and len(fields) > 19 and fields[19] == proc_start

    def _memory_mb(self, pid: int) -> Optional[int]:
        try:
            for line in (self.proc / str(pid) / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
        except (OSError, ValueError, IndexError):
            pass
        return None

    def _ancestors(self) -> set:
        """I processi da cui discende questa chiamata a deck: una sessione non chiude se stessa."""
        seen, pid = set(), self.me()
        while pid and pid > 1 and pid not in seen:
            seen.add(pid)
            fields = self._stat(pid)
            pid = int(fields[1]) if fields and len(fields) > 1 and fields[1].isdigit() else 0
        return seen

    # ---- Registro

    def _entries(self) -> list:
        """Coppie (scheda pubblica, dati interni) delle sessioni vive, dalla più vecchia."""
        mine = self._ancestors()
        entries = []
        for f in sorted(self.registry.glob("*.json")):
            try:
                d = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            pid, proc_start = d.get("pid"), str(d.get("procStart") or "")
            short = str(d.get("sessionId") or "").replace("-", "")[:8]
            if not isinstance(pid, int) or not proc_start or not ID.fullmatch(short):
                continue
            if not self._alive(pid, proc_start):
                continue  # scheda rimasta di un processo finito, o PID riusato
            folder = str(d.get("cwd") or "")
            bridge = d.get("bridgeSessionId")
            opened = folder.startswith(str(self.opened) + "/")
            public = {
                "id": hashlib.sha1(folder.encode()).hexdigest()[:8] if opened else short,
                "title": str(d.get("name") or "")[:200],
                "state": d.get("status") if d.get("status") in STATES else
                ("starting" if d.get("status") is None else "unknown"),
                "state_since": _iso(d.get("statusUpdatedAt")),
                "started": _iso(d.get("startedAt")),
                "folder": folder,
                "opened_by_deck": opened,
                "app_url": f"https://claude.ai/code/{bridge}" if isinstance(bridge, str) and BRIDGE.fullmatch(bridge)
                else None,
                "pid": pid,
                "memory_mb": self._memory_mb(pid),
                "this_session": pid in mine,
            }
            entries.append((public, {"pid": pid, "proc_start": proc_start, "folder": folder}))
        return sorted(entries, key=lambda e: e[0]["started"] or "")

    def list(self) -> list:
        return [public for public, _ in self._entries()]

    def _find(self, sid: str) -> tuple:
        for public, internal in self._entries():
            if public["id"] == sid:
                return public, internal
        raise SessionError("NOT_FOUND", {"available_ids": self.ids()})

    def ids(self) -> list:
        return [s["id"] for s in self.list()]

    # ---- Azioni

    def open(self, name: str) -> dict:
        """Apre una sessione nuova con Remote Control nella cartella ~/agentdeck/sessioni/<name>."""
        if not NAME.fullmatch(name):
            raise SessionError("BAD_NAME")
        folder = self.opened / name
        current = self.list()
        if any(s["folder"] == str(folder) for s in current):
            raise SessionError("EXISTS", {"session": next(s for s in current if s["folder"] == str(folder))})
        if sum(1 for s in current if s["opened_by_deck"]) >= MAX_OPENED:
            raise SessionError("TOO_MANY", {"max": MAX_OPENED})
        tmux_name = TMUX_PREFIX + name
        if self.run(["tmux", "has-session", "-t", f"={tmux_name}"]).returncode == 0:
            raise SessionError("EXISTS", {"tmux": tmux_name})
        folder.mkdir(parents=True, exist_ok=True)
        command = (f"{shlex.quote(str(self.claude))} remote-control --name {name} --spawn session "
                   f"|| sleep {FAILED_PANE_S}")
        started = self.run(["tmux", "new-session", "-d", "-s", tmux_name, "-x", "200", "-y", "50", "-c", str(folder),
                            command])
        if started.returncode != 0:
            raise SessionError("FAILED", {"output": (started.stderr or started.stdout).strip()[-2000:]})
        deadline, seen = self.clock() + OPEN_WAIT_S, None
        while self.clock() < deadline:
            seen = next((s for s in self.list() if s["folder"] == str(folder)), None)
            if seen and seen["app_url"]:  # registrata nell'app: è il processo che resta
                return seen
            self.sleep(1)
        if seen:
            return seen  # viva ma non ancora registrata: il link arriverà nell'elenco
        pane = self.run(["tmux", "capture-pane", "-p", "-t", f"={tmux_name}"]).stdout
        self.run(["tmux", "kill-session", "-t", f"={tmux_name}"])
        lines = [line.rstrip() for line in pane.splitlines() if line.strip()]
        raise SessionError("FAILED", {"output": "\n".join(lines[-15:])[-2000:]})

    def close(self, sid: str) -> dict:
        """Chiude una sessione: SIGINT, poi SIGTERM se non esce in CLOSE_WAIT_S secondi."""
        public, internal = self._find(sid)
        if public["this_session"]:
            raise SessionError("SELF", {"session": public})
        pid, proc_start = internal["pid"], internal["proc_start"]
        how = "SIGINT"
        self.kill(pid, signal.SIGINT)
        if not self._wait_gone(pid, proc_start):
            how = "SIGTERM"
            self.kill(pid, signal.SIGTERM)
            if not self._wait_gone(pid, proc_start):
                raise SessionError("STILL_RUNNING", {"session": public})
        if public["opened_by_deck"]:
            # il server di una sessione aperta da deck esce da sé; se la sua finestra resta, si chiude
            self.run(["tmux", "kill-session", "-t", f"={TMUX_PREFIX}{Path(internal['folder']).name}"])
        return {"session": public, "signal": how}

    def _wait_gone(self, pid: int, proc_start: str) -> bool:
        deadline = self.clock() + CLOSE_WAIT_S
        while self.clock() < deadline:
            if not self._alive(pid, proc_start):
                return True
            self.sleep(0.5)
        return not self._alive(pid, proc_start)
