"""L'agente interno su un compito: `deck agent run` (task O20.T2, piano punto 1).

Lancia `claude -p` con il prompt di sistema di AgentDeck (claude/AGENTE.md, generato da AGENTE.template.md e dalle
invarianti), gli strumenti di deck e pochi strumenti di Claude Code (Bash, Read, Grep, Glob), in bypass, con gli hook
gestiti attivi: guardia, regole deny, avvisi. Il modello è MiniMax, attraverso l'intermediario locale
(agentdeck/minimax_proxy.py): Claude Code parla con 127.0.0.1 e la chiave vera la mette l'intermediario. Lavora in
~/agentdeck/agente. Ogni corsa finisce in ~/.local/state/agentdeck/agente-runs.jsonl: ora, compito, esito, rapporto,
durata. Compito e rapporto sono testo esterno: solo nei dati (INV-4).
Attivazione automatica (O20.T3): `deck agent tick`, dal timer agentdeck-agente.timer ogni 15 minuti, lancia l'agente
solo per avvisi o obblighi nuovi o una volta al giorno; i tick vanno in agente-ticks.jsonl.
Schermata: agentdeck/components/agent.py. Documentazione: docs/agente-interno.md.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import minimax_proxy

HOME = Path(os.environ.get("HOME", "/home/agent"))
ROOT = Path(__file__).resolve().parent.parent           # /opt/agentdeck, o deck/ del repository
PROMPT = ROOT / "claude" / "AGENTE.md"
WORKDIR = HOME / "agentdeck" / "agente"
CLAUDE_BIN = HOME / ".local" / "bin" / "claude"
DECK = "/usr/local/bin/deck"
TOOLS = "Bash,Read,Grep,Glob"
TIMEOUT_S, TIMEOUT_MAX_S = 600, 1800
TASK_MAX = 4000
REPORT_MAX = 20000
DAILY_S = 24 * 3600  # il controllo giornaliero del timer (O20.T3)


def state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "agentdeck"


def base_url() -> str:
    """L'intermediario: la porta di agente.json; AGENTDECK_AGENT_BASE_URL la sostituisce (prove)."""
    return os.environ.get("AGENTDECK_AGENT_BASE_URL") or \
        f"http://127.0.0.1:{minimax_proxy.load_config()['port']}"


class AgentError(Exception):
    def __init__(self, code: str, detail: Optional[dict] = None):
        super().__init__(code)
        self.code, self.detail = code, detail or {}


class System:
    """Le operazioni reali. I test usano un finto con gli stessi metodi."""

    def run(self, argv: list, env: dict, cwd: Path, timeout: float) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd, timeout=timeout,
                                  stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired as e:
            return subprocess.CompletedProcess(argv, 124, e.stdout or "", f"timeout after {timeout} s")
        except OSError as e:
            return subprocess.CompletedProcess(argv, 127, "", str(e))

    def health(self, url: str) -> Optional[dict]:
        try:
            with urllib.request.urlopen(url + "/health", timeout=3) as r:
                return json.loads(r.read())
        except (OSError, ValueError):
            return None

    def now(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")


class Agent:
    def __init__(self, system: Optional[System] = None, prompt: Path = PROMPT, workdir: Path = WORKDIR,
                 runs: Optional[Path] = None):
        self.sys = system or System()
        self.prompt, self.workdir = prompt, workdir
        self.runs_file = runs or state_dir() / "agente-runs.jsonl"

    def runs(self, limit: int = 10) -> list:
        try:
            lines = self.runs_file.read_text().splitlines()
        except OSError:
            return []
        out = []
        for line in reversed(lines[-limit:]):
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def status(self) -> dict:
        url = base_url()
        health = self.sys.health(url)
        return {"proxy": {"url": url, "answers": health is not None,
                          "model": (health or {}).get("model"), "key_present": (health or {}).get("key_present")},
                "prompt": {"path": str(self.prompt), "present": self.prompt.is_file()},
                "workdir": str(self.workdir), "runs_file": str(self.runs_file), "recent_runs": self.runs(5)}

    def _argv(self, task: str) -> list:
        mcp = json.dumps({"mcpServers": {"deck": {"type": "stdio", "command": DECK, "args": ["mcp"]}}})
        return [str(CLAUDE_BIN), "-p", task, "--output-format", "json", "--permission-mode", "bypassPermissions",
                "--system-prompt", self.prompt.read_text(), "--tools", TOOLS, "--mcp-config", mcp,
                "--strict-mcp-config"]

    # ---- Attivazione automatica (O20.T3)

    def _screen(self, path: str) -> Optional[dict]:
        out = self.sys.run([DECK, path], dict(os.environ), self.workdir if self.workdir.is_dir() else HOME, 60)
        try:
            return json.loads(out.stdout)
        except ValueError:
            return None

    def _tick_state(self) -> dict:
        try:
            return json.loads((self.runs_file.parent / "agente-tick.json").read_text())
        except (OSError, ValueError):
            return {}

    def tick(self, timeout: int = TIMEOUT_S) -> dict:
        """Il controllo del timer: lancia l'agente solo per avvisi o obblighi nuovi, o una volta al giorno.

        Avvisi e obblighi si riconoscono per codice e id, scritti dal sistema; il compito per l'agente si compone solo
        con quelli (INV-4). Senza chiave o senza intermediario non parte e lo registra.
        """
        status, obligations = self._screen("status"), self._screen("obligations")
        codes = sorted({a["code"] for a in (status or {}).get("alerts", []) if a.get("level") in ("warning",
                                                                                                 "critical")})
        open_ids = sorted(str(o.get("id")) for o in ((obligations or {}).get("data") or {}).get("open", []))
        state = self._tick_state()
        new_codes = [c for c in codes if c not in state.get("codes", [])]
        new_ids = [i for i in open_ids if i not in state.get("obligations", [])]
        now = self.sys.now()
        last_daily = state.get("daily")
        daily_due = not last_daily or (datetime.fromisoformat(now) - datetime.fromisoformat(last_daily)).total_seconds() \
            >= DAILY_S
        reasons = ([f"new alerts: {', '.join(new_codes)}"] if new_codes else []) + \
            ([f"new obligations: {', '.join(new_ids)}"] if new_ids else []) + (["daily check"] if daily_due else [])
        tick = {"time": now, "kind": "tick", "alerts": codes, "obligations": open_ids, "reasons": reasons,
                "ran": False, "skipped": None}
        if status is None:
            tick["skipped"] = "deck status unreadable"
        elif reasons:
            task = ("Controllo automatico di AgentDeck, avviato dal timer. Motivo: " + "; ".join(reasons) + ". "
                    "Apri deck status e deck obligations, diagnostica, fai solo ciò che le tue regole ti permettono "
                    "di fare da solo e scrivi il rapporto.")
            try:
                record = self.run(task, timeout)
                tick.update(ran=True, ok=record["ok"])
                state["daily"] = now if daily_due else last_daily
            except AgentError as err:
                tick["skipped"] = err.code
        if not tick["skipped"]:
            state.update(codes=codes, obligations=open_ids)
        try:
            self.runs_file.parent.mkdir(parents=True, exist_ok=True)
            (self.runs_file.parent / "agente-tick.json").write_text(json.dumps(state) + "\n")
            with (self.runs_file.parent / "agente-ticks.jsonl").open("a") as f:
                f.write(json.dumps(tick) + "\n")
        except OSError:
            pass
        return tick

    def run(self, task: str, timeout: int = TIMEOUT_S) -> dict:
        if not task.strip():
            raise AgentError("EMPTY_TASK")
        if len(task) > TASK_MAX:
            raise AgentError("TASK_TOO_LONG", {"max": TASK_MAX})
        if not self.prompt.is_file():
            raise AgentError("NO_PROMPT", {"path": str(self.prompt)})
        url = base_url()
        health = self.sys.health(url)
        if health is None:
            raise AgentError("PROXY_DOWN", {"url": url})
        if not health.get("key_present"):
            raise AgentError("NO_KEY", {"url": url})
        self.workdir.mkdir(parents=True, exist_ok=True)
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL")}
        env.update({"ANTHROPIC_BASE_URL": url, "ANTHROPIC_API_KEY": "agentdeck-local",
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "AGENTDECK_INTERNAL_AGENT": "1"})
        started, when = time.monotonic(), self.sys.now()
        out = self.sys.run(self._argv(task), env, self.workdir, max(30, min(timeout, TIMEOUT_MAX_S)))
        result: dict = {}
        for line in reversed(out.stdout.strip().splitlines()):
            try:
                result = json.loads(line)
                break
            except ValueError:
                continue
        record = {
            "time": when, "task": task, "exit_code": out.returncode,
            "ok": out.returncode == 0 and not result.get("is_error", True),
            "report": str(result.get("result") or "")[:REPORT_MAX],
            "session_id": result.get("session_id"), "turns": result.get("num_turns"),
            "duration_s": round(time.monotonic() - started, 1), "model": health.get("model"),
            "stderr": "" if out.returncode == 0 else out.stderr[-2000:],
        }
        try:
            self.runs_file.parent.mkdir(parents=True, exist_ok=True)
            with self.runs_file.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return record
