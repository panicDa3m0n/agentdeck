"""Componenti di deck, uno per modulo. Contratto: docs/deck.md, "Aggiungere un componente"."""
from .agent import Agent
from .claude import Claude
from .claude_version import ClaudeVersion
from .home import Home
from .logs import Logs
from .network import Network
from .obligations import Obligations
from .protocol_info import ProtocolInfo
from .release import Release
from .secret import Secret
from .service import Service
from .snapshot import Snapshot
from .status import Status
from .telegram import Telegram
from .term import Term
from .update import Update


def all_components() -> list:
    """I componenti attivi. Un componente nuovo si aggiunge qui."""
    return [Agent(), Claude(), ClaudeVersion(), Home(), Logs(), Network(), Obligations(), ProtocolInfo(), Release(),
            Secret(), Service(), Snapshot(), Status(), Telegram(), Term(), Update()]
