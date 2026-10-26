"""Componenti di deck, uno per modulo. Contratto: docs/deck.md, "Aggiungere un componente"."""
from .home import Home
from .logs import Logs
from .network import Network
from .protocol_info import ProtocolInfo
from .service import Service
from .snapshot import Snapshot
from .status import Status
from .term import Term
from .update import Update


def all_components() -> list:
    """I componenti attivi. Un componente nuovo si aggiunge qui."""
    return [Home(), Logs(), Network(), ProtocolInfo(), Service(), Snapshot(), Status(), Term(), Update()]
