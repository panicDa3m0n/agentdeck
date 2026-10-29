"""Schermata "/secret": i segreti che il proprietario consegna alla Deck con una pagina monouso (O23.T1).

Mostra solo se ogni segreto c'è (dimensione, permessi, data), mai il contenuto; request genera la pagina, esposta
con il tunnel temporaneo (decisione del proprietario del 30/10/2026, INV-5) o solo in casa, e chiusa alla
consegna; cancel la chiude prima. Il valore va nel file con permessi 600 e l'agente non lo vede. Motore:
agentdeck/owner_page.py. Documentazione: docs/richieste.md.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from .. import owner_page as op
from ..engine import Component, Context, DeckError
from ..protocol import action, param, screen, sys_text


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


def via_param() -> dict:
    return param("enum", required=False, values=op.VIAS, description=sys_text(
        "internet (default): a temporary tunnel, reachable from anywhere until the answer; home: only from the home "
        "network"))


def open_request(launcher: op.Launcher) -> Optional[dict]:
    """La richiesta aperta, senza token per i segreti; con il link solo se il server gira."""
    req = op.load_request()
    if req is None:
        return None
    out = {"kind": req["kind"], "name": op.label(req), "via": req["via"], "expires": iso(req["expires_at"]),
           "expired": time.time() >= req["expires_at"], "server_running": launcher.running(), "link": op.link(req)}
    return out


def launch_error(e: op.LaunchError, path: str) -> DeckError:
    messages = {
        "no_cloudflared": ("cloudflared is not installed, so the page cannot be reached from the internet.",
                           "Install cloudflared (skill agentdeck-install-package), or use via=home."),
        "no_home_network": ("The Deck has no private address on the home network.",
                            "Check the network with `deck network`, or use via=internet."),
        "not_started": ("The page server did not start.",
                        "Read data.output and `deck logs query unit=agentdeck-pagina`, fix the cause, then retry."),
        "no_tunnel": ("The tunnel did not answer in time, so the request was closed.",
                      "Retry once; if it fails again, use via=home or read `deck logs query unit=agentdeck-pagina`."),
    }
    message, prompt = messages.get(e.code, ("The request could not start.", "Retry, or use via=home."))
    return DeckError("NOT_AVAILABLE" if e.code in ("no_cloudflared", "no_home_network") else "FAILED",
                     sys_text(message), title=sys_text("Request not started"), path=path, back=path,
                     data={"reason": e.code, "output": e.output}, prompt=sys_text(prompt))


class Secret(Component):
    path = "/secret"
    title = sys_text("Secrets")
    summary = sys_text("Secrets the owner hands to the Deck through a one-time page, never through the chat")

    def __init__(self, launcher: Optional[op.Launcher] = None):
        self.launcher = launcher or op.Launcher()

    def actions(self, ctx: Context) -> list:
        return [
            action("request", label=sys_text("Open a one-time page for the owner to hand over a secret"),
                   effect="safe", params={
                       "name": param("string", max_length=32, description=sys_text(
                           "Which secret: minimax (MiniMax API key), telegram (bot token and chat id), or another "
                           "lowercase name for any other key, kept in ~/.config/agentdeck/secrets/<name>")),
                       "via": via_param()}),
            action("cancel", label=sys_text("Close the open request before it is answered"), effect="safe"),
        ]

    def view(self, ctx: Context) -> dict:
        return screen(
            screen="secret", path=self.path, title=sys_text("Secrets"), back="/", actions=self.actions(ctx),
            data={"secrets": [op.presence(n) for n in op.known_secrets()], "request": open_request(self.launcher),
                  "recent": op.history()},
            prompt=sys_text(
                "data.secrets says which secrets are on the Deck, never their value. When one is missing and needed, "
                "run `deck secret request name=<secret>` and give the link to the owner: the page closes when the "
                "value arrives. Never ask for a secret in the chat and never read the files."))

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        if action_id == "cancel":
            req = self.launcher.cancel()
            return screen(screen="secret.cancelled", path=self.path, title=sys_text("Request closed"),
                          status="done", back=self.path, actions=self.actions(ctx),
                          data={"cancelled": {"kind": req["kind"], "name": op.label(req)} if req else None},
                          prompt=sys_text("No request is open now: the page no longer works."))
        name = params["name"]
        if not op.SLUG.fullmatch(name):
            raise DeckError("BAD_PARAM", sys_text("A secret name is lowercase letters, digits and dashes."),
                            title=sys_text("Invalid parameters"), path=self.path, back=self.path, field_name="name",
                            prompt=sys_text("Use minimax, telegram or a short lowercase name such as openai-key."))
        try:
            req = self.launcher.start("secret", params.get("via", "internet"), name=name)
        except op.LaunchError as e:
            raise launch_error(e, self.path) from None
        return screen(
            screen="secret.requested", path=self.path, title=sys_text("Page ready for {name}", name=name),
            status="done", back=self.path, actions=self.actions(ctx),
            data={"request": {"name": name, "via": req["via"], "link": op.link(req), "expires": iso(req["expires_at"]),
                              "unit": op.UNIT},
                  "secret": op.presence(name)},
            prompt=sys_text(
                "Give data.request.link to the owner: it works once, until data.request.expires, and closes when the "
                "value arrives; you never see the value. Do not ask for it in the chat. When the owner says it is "
                "done, check with `deck secret` that it is present and that data.recent shows received."))
