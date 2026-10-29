"""Riga di comando di brain: come deck, ma con i componenti del Brain.

Uso: brain [indirizzo] [azione] [nome=valore ...] [--pretty]
     brain mcp   (le stesse schermate come server MCP su stdio, strumenti mcp__brain__*)
Documentazione: docs/brain.md.
"""
from __future__ import annotations

import sys
from typing import Optional

from . import COMMAND, INSTRUCTIONS, START, TITLE, make_brain
from ..cli import run


def main(argv: Optional[list] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["mcp"]:  # mcp non è un indirizzo, come per deck
        from ..mcp import Server, serve
        return serve(server=Server(make_brain, name=COMMAND, title=TITLE, instructions=INSTRUCTIONS, start=START))
    return run(make_brain(), argv)
