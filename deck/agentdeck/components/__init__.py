"""Componenti di deck, uno per modulo. Contratto: docs/deck.md, "Aggiungere un componente"."""
from .home import Home
from .network import Network
from .protocol_info import ProtocolInfo
from .service import Service
from .snapshot import Snapshot
from .status import Status


def all_components() -> list:
    """I componenti attivi. Un componente nuovo si aggiunge qui."""
    return [Home(), Network(), ProtocolInfo(), Service(), Snapshot(), Status()]
