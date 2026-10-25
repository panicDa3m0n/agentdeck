"""AgentDeck: lo strato agentico del sistema, esposto dal comando deck.

Documentazione: docs/deck.md. Specifica del protocollo: docs/protocollo.md.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def version() -> str:
    """Versione di AgentDeck: il VERSION copiato dall'installazione, altrimenti quello del repository."""
    for candidate in (_ROOT / "VERSION", _ROOT.parent / "VERSION"):
        if candidate.is_file():
            return candidate.read_text().strip()
    return "dev"
