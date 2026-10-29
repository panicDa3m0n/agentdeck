"""Schermata "/secret": i segreti che il proprietario consegna alla Deck senza passare dalla chat (O23.T1).

Mostra solo se ogni segreto c'è (dimensione, permessi, data), mai il contenuto; request apre una richiesta web
monouso nella rete di casa, eseguita dall'unità a tempo agentdeck-segreto; cancel la chiude. Logica e server:
agentdeck/secret_drop.py. Documentazione: docs/segreti.md.
"""
from __future__ import annotations

import os
import pwd
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .. import secret_drop as sd
from ..engine import Component, Context, DeckError
from ..protocol import action, param, screen, sys_text

SERVER = Path(sd.__file__).resolve()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


class Secret(Component):
    path = "/secret"
    title = sys_text("Secrets")
    summary = sys_text("Secrets the owner hands to the Deck through a one-time web link, never through the chat")

    def __init__(self, sh: Callable = subprocess.run, lan: Callable[[], Optional[str]] = sd.lan_address,
                 wait_s: float = 5.0):
        self.sh, self.lan, self.wait_s = sh, lan, wait_s

    def actions(self, ctx: Context) -> list:
        return [
            action("request", label=sys_text("Open a one-time web link for the owner to hand over a secret"),
                   effect="safe", params={"name": param("enum", values=list(sd.SLOTS), description=sys_text(
                       "Which secret: minimax (the MiniMax API key) or telegram (bot token and chat id)"))}),
            action("cancel", label=sys_text("Close the open request before it expires"), effect="safe"),
        ]

    def _cmd(self, argv: list):
        return self.sh(argv, capture_output=True, text=True, timeout=30)

    def _running(self) -> bool:
        return self._cmd(["systemctl", "is-active", sd.UNIT]).stdout.strip() in ("active", "activating")

    def _request_data(self) -> Optional[dict]:
        req = sd.load_request()
        if req is None:
            return None
        return {"name": req["name"], "url": sd.url(req), "expires": _iso(req["expires_at"]),
                "expired": time.time() >= req["expires_at"], "server_running": self._running()}

    def view(self, ctx: Context) -> dict:
        return screen(
            screen="secret", path=self.path, title=sys_text("Secrets"), back="/", actions=self.actions(ctx),
            data={"slots": [sd.presence(n) for n in sd.SLOTS], "request": self._request_data(),
                  "recent": sd.history()},
            prompt=sys_text(
                "data.slots says which secrets are on the Deck, never their value. When one is missing and needed, "
                "open a link with `deck secret request name=<secret>` and give it to the owner: they paste the "
                "value in the page and it goes straight to the file. Never ask for a secret in the chat and never "
                "read the files."))

    def _stop(self) -> None:
        self._cmd(["sudo", "-n", "systemctl", "stop", sd.UNIT])
        self._cmd(["sudo", "-n", "systemctl", "reset-failed", sd.UNIT])

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        if action_id == "cancel":
            req = sd.load_request()
            self._stop()
            if req is not None:
                sd.clear_request()
                sd.record(req["name"], "cancelled")
            return screen(screen="secret.cancelled", path=self.path, title=sys_text("Request closed"),
                          status="done", back=self.path, actions=self.actions(ctx),
                          data={"cancelled": req["name"] if req else None, "server_running": self._running()},
                          prompt=sys_text("No request is open now: the link no longer works."))

        name = params["name"]
        host = self.lan()
        if host is None:
            raise DeckError("NOT_AVAILABLE", sys_text("The Deck has no private address on the home network, so "
                                                      "the link cannot be opened without exposing it."),
                            title=sys_text("No home network"), path=self.path, back=self.path,
                            prompt=sys_text("Check the network with `deck network`. The owner can still write the "
                                            "file over SSH; never ask for the value in the chat."))
        self._stop()  # una richiesta alla volta: la nuova sostituisce quella aperta
        req = sd.new_request(name, host)
        user = pwd.getpwuid(os.getuid()).pw_name
        env = [f"--setenv=HOME={Path.home()}"] + [f"--setenv={k}={os.environ[k]}" for k in
                                                   ("XDG_STATE_HOME", "XDG_CONFIG_HOME") if os.environ.get(k)]
        started = self._cmd(["sudo", "-n", "systemd-run", f"--unit={sd.UNIT}", f"--uid={user}", f"--gid={user}",
                             f"--property=RuntimeMaxSec={sd.TTL_S + 60}", "--collect", "--quiet", *env,
                             sys.executable, str(SERVER)])
        running = started.returncode == 0
        deadline = time.monotonic() + self.wait_s
        while running and not self._running() and time.monotonic() < deadline:
            time.sleep(0.2)
        running = running and self._running()
        if not running:
            sd.clear_request()
            sd.record(name, "not_started")
            raise DeckError("FAILED", sys_text("The one-time server did not start."), title=sys_text("Not started"),
                            path=self.path, back=self.path,
                            data={"unit": sd.UNIT, "output": (started.stderr or started.stdout or "")[-1000:]},
                            prompt=sys_text("Read data.output and the unit's log with `deck logs query "
                                            "unit={unit}`, fix the cause, then request again.", unit=sd.UNIT))
        return screen(
            screen="secret.requested", path=self.path, title=sys_text("Link ready for {name}", name=name),
            status="done", back=self.path, actions=self.actions(ctx),
            data={"request": {"name": name, "url": sd.url(req), "expires": _iso(req["expires_at"]),
                              "server_running": True, "unit": sd.UNIT},
                  "slot": sd.presence(name)},
            prompt=sys_text(
                "Give data.request.url to the owner. It works only from the home network, once, until "
                "data.request.expires; the value goes straight to the file and you never see it. Do not ask for the "
                "value in the chat. When the owner says it is done, check with `deck secret` that data.slots shows "
                "it present and data.recent shows received."))
