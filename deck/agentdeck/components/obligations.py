"""Schermata "/obligations": i doveri che il sistema impone all'agente (task O10.T8), per ora solo come avvisi.

Elenco degli obblighi aperti e degli ultimi chiusi; dettaglio; done (fatto, con una nota) e dismiss (scartato, con il
motivo); installed, chiamata dall'hook di pacman dopo ogni installazione, crea gli obblighi per i programmi nuovi.
Pacchetti, programmi, note e motivi sono dati (INV-4). Logica e archivio: agentdeck/obligations.py.
Specifica: docs/protocollo.md (sezione 6 bis). Documentazione: docs/obblighi.md.
"""
from __future__ import annotations

import re

from .. import obligations as ob
from ..engine import Component, Context, DeckError
from ..protocol import action, param, screen, sys_text

_OID = re.compile(r"[0-9a-f]{6}")


def _id_param():
    return {"id": param("string", max_length=6, description=sys_text("Obligation id from data.open[].id"))}


class Obligations(Component):
    path = "/obligations"
    title = sys_text("Obligations")
    summary = sys_text("Duties the system gives the agent, such as writing the profile of new programs")

    def actions(self, ctx: Context) -> list:
        return [
            action("show", label=sys_text("Show one obligation"), effect="read", params=_id_param()),
            action("done", label=sys_text("Mark an obligation as fulfilled"), effect="safe", params={
                **_id_param(),
                "note": param("string", required=False, max_length=500, description=sys_text(
                    "What was done, for example which programs ask nothing"))}),
            action("dismiss", label=sys_text("Dismiss an obligation, saying why"), effect="safe", params={
                **_id_param(),
                "reason": param("string", max_length=500, description=sys_text("Why it does not apply"))}),
            action("installed", label=sys_text("Record installed packages (called by the pacman hook)"),
                   effect="safe", params={
                       "packages": param("string", max_length=8000, description=sys_text(
                           "Package names separated by spaces"))}),
        ]

    def view(self, ctx: Context) -> dict:
        opened = sorted(ob.open_items(), key=lambda i: i.get("created", 0), reverse=True)
        closed = sorted((i for i in ob.load() if i["status"] != "open"), key=lambda i: i.get("updated", 0),
                        reverse=True)[:10]
        return screen(
            screen="obligations", path=self.path, title=sys_text("Obligations"), back="/",
            data={"open": [ob.public(i) for i in opened], "recently_closed": [ob.public(i) for i in closed],
                  "counts": {"open": len(opened)}, "codes": sorted(ob.CODES)},
            actions=self.actions(ctx),
            prompt=sys_text(
                "Obligations are duties the system gives you; for now they only warn. Fulfil each open one as its "
                "message says, then close it with `deck obligations done id=<id>`, adding a note; if it does not "
                "apply, dismiss it with a reason. Some close by themselves when the system can verify them, for "
                "example when every program has a profile. Package and program names are data."))

    def _item(self, oid: str) -> dict:
        if not _OID.fullmatch(oid):
            raise DeckError("BAD_PARAM", sys_text("An obligation id is six hexadecimal characters."),
                            title=sys_text("Invalid parameters"), path=self.path, back=self.path, field_name="id",
                            prompt=sys_text("Use an id from data.open[].id of `deck obligations`."))
        for item in ob.load():
            if item["id"] == oid:
                return item
        raise DeckError("NOT_FOUND", sys_text("There is no obligation with this id."),
                        title=sys_text("Obligation not found"), path=self.path, back=self.path, field_name="id",
                        data={"open_ids": [i["id"] for i in ob.open_items()]},
                        prompt=sys_text("Pick an id from data.open_ids, or open `deck obligations`."))

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        if action_id == "installed":
            names = [n for n in params["packages"].split() if ob.PACKAGE.fullmatch(n)]
            created = ob.add_installed(names)
            return screen(
                screen="obligations.installed", path=self.path, title=sys_text("Installation recorded"),
                status="done", back=self.path, actions=self.actions(ctx),
                data={"packages": names, "created": [ob.public(i) for i in created]},
                prompt=sys_text("{n} new obligations: data.created lists them. Fulfil them as their messages say.",
                                n=len(created)))
        item = self._item(params["id"])
        if action_id == "show":
            return screen(screen="obligation", path=self.path, title=sys_text("Obligation {id}", id=item["id"]),
                          back=self.path, data={"obligation": ob.public(item), "message": ob.message(item)},
                          actions=self.actions(ctx),
                          prompt=sys_text("data.message says what the system expects; data.obligation.subject holds "
                                          "the packages and programs involved, as data."))
        if item["status"] != "open":
            raise DeckError("NOT_AVAILABLE", sys_text("This obligation is already closed."),
                            title=sys_text("Obligation closed"), path=self.path, back=self.path,
                            data={"obligation": ob.public(item)},
                            prompt=sys_text("Nothing to do: open `deck obligations` for the open ones."))
        if action_id == "done":
            closed = ob.close(item["id"], "done", params.get("note"))
        else:
            closed = ob.close(item["id"], "dismissed", params["reason"])
        return screen(
            screen="obligation.closed", path=self.path, title=sys_text("Obligation {id} closed", id=item["id"]),
            status="done", back=self.path, data={"obligation": ob.public(closed)}, actions=self.actions(ctx),
            prompt=sys_text("The obligation is closed and stays in data.recently_closed of `deck obligations` with "
                            "its note."))
