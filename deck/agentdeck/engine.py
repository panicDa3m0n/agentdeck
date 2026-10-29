"""Motore di deck: indirizzi, componenti, parametri, conferme ed errori (protocollo, sezioni 2-8).

Specifica: docs/protocollo.md. Documentazione del motore e contratto dei componenti: docs/deck.md.
"""
from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import confirm as confirm_codes
from . import version
from .protocol import SysText, action, child, error_info, is_path, param, screen, sys_text

_INT = re.compile(r"-?[0-9]+")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_BOOLS = {"true": True, "yes": True, "1": True, "false": False, "no": False, "0": False}


@dataclass
class Context:
    """Quello che un componente sa della chiamata in corso."""

    deck: "Deck"
    host: str = field(default_factory=socket.gethostname)
    version: str = field(default_factory=version)

    def uptime_s(self) -> Optional[int]:
        try:
            return int(float(Path("/proc/uptime").read_text().split()[0]))
        except (OSError, ValueError, IndexError):
            return None


@dataclass
class Preview:
    """Anteprima di un'azione distruttiva: cosa cambia, cosa resta, come si torna indietro."""

    screen: str
    title: SysText
    data: dict
    changes: list
    untouched: list
    undo: str
    reboot_required: bool
    prompt: Callable[[str], SysText]  # riceve il codice di conferma


class DeckError(Exception):
    """Errore del protocollo: diventa una schermata di errore (sezione 8)."""

    def __init__(self, code: str, message: SysText, *, prompt: SysText, title: Optional[SysText] = None,
                 field_name: Optional[str] = None, data: Optional[dict] = None, path: str = "/",
                 back: Optional[str] = "/", children: Optional[list] = None):
        super().__init__(code)
        self.code, self.message, self.prompt = code, message, prompt
        self.title = title or sys_text("Error")
        self.field_name, self.data = field_name, data or {}
        self.path, self.back, self.children = path, back, children


class Component:
    """Contratto di un componente (docs/deck.md, "Aggiungere un componente").

    path: indirizzo; title e summary: come appare tra i figli della schermata principale.
    view(ctx): la schermata in stato "ok". actions(ctx): le azioni possibili ora.
    run(ctx, action_id, params): esegue un'azione e restituisce la schermata "done".
    preview(ctx, action_id, params): per le azioni distruttive, l'anteprima da confermare.
    """

    path = "/"
    title = sys_text("Component")
    summary = sys_text("Component")

    def view(self, ctx: Context) -> dict:
        raise NotImplementedError

    def actions(self, ctx: Context) -> list:
        return []

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        raise NotImplementedError

    def preview(self, ctx: Context, action_id: str, params: dict) -> Preview:
        raise NotImplementedError


class Deck:
    """L'insieme dei componenti e le regole comuni per usarli.

    command è il comando che serve queste schermate, citato nei testi: deck, oppure brain per il Brain
    (docs/brain.md), che usa lo stesso motore con componenti suoi. obligations dice se le schermate portano con sé
    gli obblighi aperti del sistema (protocollo, sezione 6 bis): sì per deck, no per brain.
    """

    def __init__(self, components: list, command: str = "deck", obligations: bool = True):
        self.components = {c.path: c for c in components}
        self.command, self.obligations = command, obligations

    def home_children(self) -> list:
        return [child(c.path, title=c.title, summary=c.summary)
                for path, c in sorted(self.components.items()) if path != "/"]

    def handle(self, path: str, action_id: Optional[str], raw: dict) -> dict:
        """Risponde a una chiamata con una schermata; gli errori del protocollo escono come DeckError."""
        ctx = Context(deck=self)
        component = self.components.get(path)
        if component is None:
            raise DeckError("NOT_FOUND", sys_text("There is no screen at this address."),
                            title=sys_text("Address not found"), path=path if is_path(path) else "/",
                            children=self.home_children(),
                            prompt=sys_text("Open one of the components listed in nav.children, or run `{cmd}` "
                                            "to start from the home screen.", cmd=self.command))
        if action_id is None:
            if raw:
                raise self._bad_param(component, None, sys_text("Parameters need an action: "
                                                                "`{cmd} <path> <action> name=value`.",
                                                                cmd=self.command))
            return component.view(ctx)

        specs = {a["id"]: a for a in component.actions(ctx)}
        spec = specs.get(action_id)
        if spec is None:
            raise DeckError("NOT_FOUND", sys_text("This screen has no such action."),
                            title=sys_text("Action not found"), path=path, back=path,
                            data={"available_actions": sorted(specs)},
                            prompt=sys_text("Use one of data.available_actions, or open `{cmd} {path}` to see "
                                            "each action with its parameters.", cmd=self.command, path=path))
        if not spec["available"]:
            raise DeckError("NOT_AVAILABLE", spec["reason"], title=sys_text("Action not available"),
                            path=path, back=path,
                            prompt=sys_text("This action cannot run now: the message explains why. Open "
                                            "`{cmd} {path}` to check the current state.", cmd=self.command,
                                            path=path))

        raw = dict(raw)
        token = raw.pop("confirm", None) if spec["confirm"] else None
        params = self._parse(component, spec, raw)
        if not spec["confirm"]:
            return component.run(ctx, action_id, params)
        if token is None:
            return self._confirm_screen(ctx, component, spec, params)
        if not confirm_codes.consume(token, path, action_id, params):
            raise DeckError("CONFIRM_INVALID", sys_text("The confirmation code is wrong, expired, or was "
                                                        "issued for another action."),
                            title=sys_text("Confirmation refused"), path=path, back=path, field_name="confirm",
                            prompt=sys_text("Repeat the call without confirm= to get a fresh preview and code, "
                                            "check the preview, then confirm with the new code."))
        return component.run(ctx, action_id, params)

    def _confirm_screen(self, ctx: Context, component: Component, spec: dict, params: dict) -> dict:
        pv = component.preview(ctx, spec["id"], params)
        token, expires = confirm_codes.issue(component.path, spec["id"], params)
        confirm_params = dict(spec["params"])
        confirm_params["confirm"] = param("string", description=sys_text("Confirmation code from confirm.token"))
        confirm_action = action(spec["id"], label=spec["label"], effect=spec["effect"], params=confirm_params)
        return screen(screen=pv.screen, path=component.path, title=pv.title, status="confirm", data=pv.data,
                      actions=[confirm_action], back=component.path, prompt=pv.prompt(token),
                      confirm={"token": token, "expires": expires,
                               "preview": {"changes": pv.changes, "untouched": pv.untouched, "undo": pv.undo,
                                           "reboot_required": pv.reboot_required}})

    def _bad_param(self, component: Component, name: Optional[str], message: SysText,
                   code: str = "BAD_PARAM") -> DeckError:
        return DeckError(code, message, title=sys_text("Invalid parameters"), path=component.path,
                         back=component.path,
                         field_name=name if name and _NAME.fullmatch(name) else None,
                         prompt=sys_text("Fix the parameter named in error.field and repeat the call. Open "
                                         "`{cmd} {path}` to see each action with its parameters.",
                                         cmd=self.command, path=component.path))

    def _parse(self, component: Component, spec: dict, raw: dict) -> dict:
        """Valida i parametri nome=valore contro la specifica dell'azione (sezione 5)."""
        params: dict = {}
        for name in raw:
            if name not in spec["params"]:
                raise self._bad_param(component, name, sys_text("Unknown parameter for this action."))
        for name, p in spec["params"].items():
            if name not in raw:
                if p["required"]:
                    raise self._bad_param(component, name, sys_text("A required parameter is missing."),
                                          code="MISSING_PARAM")
                continue
            value = raw[name]
            if p["type"] == "int":
                if not _INT.fullmatch(value):
                    raise self._bad_param(component, name, sys_text("This parameter must be an integer."))
                params[name] = int(value)
            elif p["type"] == "bool":
                if value.lower() not in _BOOLS:
                    raise self._bad_param(component, name, sys_text("This parameter must be true or false."))
                params[name] = _BOOLS[value.lower()]
            elif p["type"] == "enum":
                if value not in p["values"]:
                    raise self._bad_param(component, name, sys_text("This value is not among the allowed ones."))
                params[name] = value
            else:
                limit = p.get("max_length")
                if limit is not None and len(value) > limit:
                    raise self._bad_param(component, name, sys_text("This text is too long (max {n}).", n=limit))
                params[name] = value
        return params

    def error_screen(self, e: DeckError) -> dict:
        return screen(screen="error", path=e.path, title=e.title, status="error", data=e.data, back=e.back,
                      children=e.children or [], prompt=e.prompt,
                      error=error_info(e.code, e.message, e.field_name))

    def failed_screen(self, exc: BaseException, extra: Optional[dict] = None) -> dict:
        """Un guasto interno: i dettagli tecnici vanno solo nei dati, mai nelle istruzioni."""
        data: dict = {"exception": type(exc).__name__, "detail": str(exc)}
        data.update(extra or {})
        return screen(screen="error", path="/", title=sys_text("Internal error"), status="error", data=data,
                      back=None, children=self.home_children(),
                      prompt=sys_text("{cmd} failed internally. Report data.exception and data.detail; do not "
                                      "repeat the same call unchanged.", cmd=self.command),
                      error=error_info("FAILED", sys_text("The operation failed inside {cmd}.", cmd=self.command)))


def call_tokens(args: list) -> tuple:
    """Divide gli argomenti in indirizzo, azione e parametri: deck [indirizzo] [azione] [nome=valore ...]
    (lo stesso per brain)."""
    words = [a for a in args if "=" not in a]
    raw: dict = {}
    for a in args:
        if "=" in a:
            name, _, value = a.partition("=")
            raw[name] = value
    path = words[0] if words else "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    action_id = words[1] if len(words) > 1 else None
    return path, action_id, raw, words[2:]
