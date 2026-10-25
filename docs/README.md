# Indice della documentazione

Ogni documento descrive un argomento e rimanda al codice che lo realizza; ogni script rimanda al suo
documento (invariante INV-9). Quando si modifica il codice, si aggiorna il documento nello stesso commit.

## Progetto

- [../README.md](../README.md): panoramica di AgentDeck e struttura del repository.
- [../PRINCIPI.md](../PRINCIPI.md): principi (agent-first, sviluppo incrementale, livello di intervento),
  visione e decisioni prese.
- [../CHANGELOG.md](../CHANGELOG.md): storia delle versioni.
- [../PROGETTO.md](../PROGETTO.md) e [../ROADMAP.md](../ROADMAP.md): dossier e roadmap generati dalla
  governance; non si modificano a mano.

## Macchina

- [hardware.md](hardware.md): componenti della Steam Deck LCD, dischi, rete, schermo, limiti noti.

## Installazione e recupero

- [chiavetta-live.md](chiavetta-live.md): chiavetta di avvio con Wi-Fi e SSH automatici.
  Codice: [../live/prepare-stick.sh](../live/prepare-stick.sh), [../live/live-setup.sh](../live/live-setup.sh).
- [installazione.md](installazione.md): installazione di Arch a fasi e configurazione del sistema.
  Codice: [../install/install.sh](../install/install.sh), [../install/post-install.sh](../install/post-install.sh).

## Interfaccia agentica

- [protocollo.md](protocollo.md): protocollo di `deck` (schermate JSON, azioni, navigazione, errori,
  conferme con anteprima, autoprompting, sicurezza del canale istruzioni).

## Uso quotidiano

- [accesso.md](accesso.md): accesso SSH dell'agente, indirizzo della Deck, sicurezza, snapshot e recupero.
- [sviluppo.md](sviluppo.md): repository git, identità, remote GitHub, versioni, governance.
