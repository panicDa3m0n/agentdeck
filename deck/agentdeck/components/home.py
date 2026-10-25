"""Schermata principale "/": il punto di partenza di ogni agente (protocollo, sezione 4).

Specifica: docs/protocollo.md. Documentazione: docs/deck.md.
"""
from ..engine import Component, Context
from ..protocol import screen, sys_text


class Home(Component):
    path = "/"
    title = sys_text("AgentDeck")
    summary = sys_text("Home: the list of system components")

    def view(self, ctx: Context) -> dict:
        return screen(
            screen="home", path="/", title=sys_text("AgentDeck"), back=None,
            data={"host": ctx.host, "version": ctx.version, "uptime_s": ctx.uptime_s()},
            children=ctx.deck.home_children(),
            prompt=sys_text("This is the AgentDeck home. Each child in nav.children is a system component: open "
                            "one with `deck <path>`. Every screen has the same shape: read facts in data, act "
                            "only through actions. `deck /protocol` describes the rules."))
