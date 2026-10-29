"""Telegram, il canale a due vie fra il proprietario e AgentDeck (task O21.T1, piano punto 3).

Il ponte chiede gli aggiornamenti al bot con long polling: nessuna porta esposta (INV-5). Risponde solo al chat id del
proprietario: i suoi messaggi diventano compiti dell'agente interno (agentdeck/agent.py) e il rapporto torna in chat;
/stato dà un riassunto di deck status; i rapporti dei controlli automatici del timer (O20.T3) arrivano da soli. Gli
altri mittenti sono ignorati e registrati in telegram-unknown.jsonl. Token e chat id stanno solo sulla Deck, in
~/.config/agentdeck/telegram.json (600, INV-6). I messaggi del proprietario sono istruzioni dell'utente; tutto il
resto che passa di qui (rapporti, risposte di Telegram) è dato. Servizio: claude/agentdeck-telegram.service.
Schermata: agentdeck/components/telegram.py. Documentazione: docs/telegram.md.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

HOME = Path(os.environ.get("HOME", "/home/agent"))
CONFIG = HOME / ".config" / "agentdeck" / "telegram.json"
API = "https://api.telegram.org"
POLL_S = 50
MESSAGE_MAX = 3900
AUTO_PREFIX = "Controllo automatico"   # i compiti del timer (agent.py, tick)
HELP = ("AgentDeck. Scrivimi cosa fare e lo passo all'agente interno: ti rispondo con il suo rapporto.\n"
        "/stato  riassunto dello stato della Deck\n/help  questo messaggio")


def state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "agentdeck"


def load_config(path: Path = CONFIG) -> Optional[dict]:
    try:
        cfg = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not cfg.get("token") or not str(cfg.get("chat_id", "")).lstrip("-").isdigit():
        return None
    cfg.setdefault("api", API)
    return cfg


class TelegramError(Exception):
    pass


class Bot:
    def __init__(self, cfg: dict):
        self.base = f"{cfg['api'].rstrip('/')}/bot{cfg['token']}"

    def call(self, method: str, params: dict, timeout: float = 30) -> dict:
        req = urllib.request.Request(f"{self.base}/{method}", data=json.dumps(params).encode(), method="POST",
                                     headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
        except (OSError, ValueError) as e:
            raise TelegramError(type(e).__name__) from None  # mai l'URL nell'errore: contiene il token
        if not data.get("ok"):
            raise TelegramError(str(data.get("description", "not ok"))[:200])
        return data.get("result")

    def send(self, chat_id, text: str) -> int:
        """Manda un testo, diviso in più messaggi se è lungo. Restituisce quanti ne ha mandati."""
        parts = [text[i:i + MESSAGE_MAX] for i in range(0, len(text), MESSAGE_MAX)] or ["(vuoto)"]
        for part in parts:
            self.call("sendMessage", {"chat_id": chat_id, "text": part, "disable_web_page_preview": True})
        return len(parts)


def _deck(path: str) -> Optional[dict]:
    try:
        out = subprocess.run(["/usr/local/bin/deck", path], capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def status_summary(status: Optional[dict]) -> str:
    if not status:
        return "deck status non risponde."
    d = status.get("data") or {}
    alerts = status.get("alerts") or []
    temps = (d.get("sensors") or {}).get("temps_c") or {}
    lines = [f"AgentDeck {(status.get('meta') or {}).get('version', '?')} — {len(alerts)} avvisi"]
    lines += [f"• [{a.get('level')}] {a.get('code')}" for a in alerts]
    lines.append(f"APU {temps.get('apu', '?')} °C · batteria {(d.get('battery') or {}).get('percent', '?')}% · "
                 f"servizi falliti {len((d.get('services') or {}).get('failed') or [])}")
    return "\n".join(lines)


class Bridge:
    def __init__(self, cfg: dict, bot: Optional[Bot] = None, agent=None, deck=_deck, state: Optional[Path] = None):
        self.cfg, self.bot = cfg, bot or Bot(cfg)
        self.chat_id = int(cfg["chat_id"])
        self.deck = deck
        self.state_path = (state or state_dir()) / "telegram-state.json"
        self.unknown_path = self.state_path.parent / "telegram-unknown.jsonl"
        if agent is None:
            from . import agent as ag
            agent = ag.Agent()
        self.agent = agent
        self.state = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return {"offset": 0, "runs_seen": None}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state) + "\n")

    def _unknown(self, msg: dict) -> None:
        chat = msg.get("chat") or {}
        entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "chat_id": chat.get("id"),
                 "from": (msg.get("from") or {}).get("username"), "text": str(msg.get("text", ""))[:500]}
        with self.unknown_path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def handle(self, msg: dict) -> None:
        if (msg.get("chat") or {}).get("id") != self.chat_id:
            self._unknown(msg)
            return
        text = str(msg.get("text") or "").strip()
        if not text:
            self.bot.send(self.chat_id, "Per ora leggo solo messaggi di testo.")
        elif text in ("/start", "/help"):
            self.bot.send(self.chat_id, HELP)
        elif text == "/stato":
            self.bot.send(self.chat_id, status_summary(self.deck("status")))
        else:
            self.bot.send(self.chat_id, "Ricevuto: lo passo all'agente interno.")
            try:
                record = self.agent.run(text)
                reply = record["report"] or "(nessun rapporto)"
                if not record["ok"]:
                    reply = f"La corsa non è riuscita (uscita {record['exit_code']}).\n{reply}"
            except Exception as e:  # noqa: BLE001 - qualunque guasto torna al proprietario come testo
                reply = f"L'agente interno non è partito: {getattr(e, 'code', type(e).__name__)}."
            self.bot.send(self.chat_id, reply)

    def forward_automatic(self) -> int:
        """Manda al proprietario i rapporti dei controlli automatici non ancora inviati."""
        runs = self.agent.runs_file
        try:
            lines = runs.read_text().splitlines()
        except OSError:
            lines = []
        if self.state.get("runs_seen") is None:  # alla prima accensione non si rimanda la storia
            self.state["runs_seen"] = len(lines)
            return 0
        sent = 0
        for line in lines[self.state["runs_seen"]:]:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if str(record.get("task", "")).startswith(AUTO_PREFIX):
                head = "Controllo automatico" + ("" if record.get("ok") else " (non riuscito)") + ":\n"
                self.bot.send(self.chat_id, head + (record.get("report") or "(nessun rapporto)"))
                sent += 1
        self.state["runs_seen"] = len(lines)
        return sent

    def once(self, poll_s: int = POLL_S) -> int:
        updates = self.bot.call("getUpdates", {"offset": self.state.get("offset", 0), "timeout": poll_s,
                                               "allowed_updates": ["message"]}, timeout=poll_s + 15) or []
        for update in updates:
            self.state["offset"] = int(update["update_id"]) + 1
            self._save()  # prima di eseguire: un compito non si ripete dopo un riavvio
            if update.get("message"):
                self.handle(update["message"])
        self.forward_automatic()
        self._save()
        return len(updates)


def send_to_owner(text: str, cfg: Optional[dict] = None) -> int:
    cfg = cfg or load_config()
    if cfg is None:
        raise TelegramError("not configured")
    return Bot(cfg).send(int(cfg["chat_id"]), text)


def main() -> int:
    waiting = False
    while True:
        cfg = load_config()
        if cfg is None:
            if not waiting:
                print("telegram: ~/.config/agentdeck/telegram.json missing or incomplete; waiting", flush=True)
                waiting = True
            time.sleep(60)
            continue
        waiting = False
        bridge = Bridge(cfg)
        print(f"telegram: bridge on for chat {cfg['chat_id']}", flush=True)
        while load_config() == cfg:
            try:
                bridge.once()
            except TelegramError as e:
                print(f"telegram: {e}", flush=True)
                time.sleep(15)


if __name__ == "__main__":
    sys.exit(main())
