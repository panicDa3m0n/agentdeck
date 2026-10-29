"""Schermata principale di brain, "/": i componenti del Brain. Documentazione: docs/brain.md."""
from ...engine import Component, Context
from ...protocol import screen, sys_text


class Home(Component):
    path = "/"
    title = sys_text("Brain")
    summary = sys_text("Home: the components of the agent's brain")

    def view(self, ctx: Context) -> dict:
        return screen(
            screen="brain.home", path="/", title=sys_text("Brain"), back=None,
            data={"host": ctx.host, "version": ctx.version},
            children=ctx.deck.home_children(),
            prompt=sys_text("This is the Brain of AgentDeck: the agent's own processes, starting from memory. "
                            "`deck` runs the system; `brain` holds what the agent knows. Open a child in "
                            "nav.children with `brain <path>`, or through the MCP tools mcp__brain__open and "
                            "mcp__brain__<component>_<action>."))
