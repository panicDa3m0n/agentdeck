"""Componenti del Brain, uno per modulo, con lo stesso contratto di quelli di deck (docs/deck.md)."""
from .home import Home
from .memory import Memory


def all_components() -> list:
    """I componenti attivi del Brain. Uno nuovo si aggiunge qui."""
    return [Home(), Memory()]
