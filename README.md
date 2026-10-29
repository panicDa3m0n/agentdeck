# AgentDeck

Una Steam Deck trasformata in un sistema operativo **agent-first**: un server domestico a basso consumo
con Arch Linux, gestito interamente da un agente AI. L'umano è al massimo spettatore; la grafica, quando
arriverà, sarà un canale con cui l'agente mostra le cose all'umano.

Ogni componente del sistema viene riprogettato per l'uso agentico con due tecnologie:

- **Interattività:** ogni risposta del sistema è una schermata in JSON strutturato, con dati, azioni,
  navigazione, errori e conferme come anteprima delle conseguenze.
- **Autoprompting:** il sistema dà all'agente le istruzioni giuste per il contesto in cui si trova.

I principi completi sono in [PRINCIPI.md](PRINCIPI.md).

## Stato

- Arch Linux installato sull'NVMe della Deck, con snapshot Btrfs avviabili da GRUB.
- Accesso dell'agente via SSH: `ssh agentdeck` (vedi [docs/accesso.md](docs/accesso.md)).
- `deck`, l'interfaccia di sistema per agenti, installata sulla Deck: `ssh agentdeck deck`, e come server MCP
  per Claude Code con `deck mcp` (vedi [docs/deck.md](docs/deck.md) e il protocollo in
  [docs/protocollo.md](docs/protocollo.md)).
- `brain`, la memoria dell'agente, separata da `deck` ma sullo stesso protocollo: `brain /memory`, e come server MCP
  con `brain mcp` (vedi [docs/brain.md](docs/brain.md)).
- Lo schermo della Deck è calmo e mostra interfacce effimere quando servono, per ora le sessioni Claude
  (vedi [docs/interfacce.md](docs/interfacce.md)); i comandi dell'agente restano nel registro
  ([docs/schermo.md](docs/schermo.md)).
- Versione corrente nel file [VERSION](VERSION); storia delle versioni in [CHANGELOG.md](CHANGELOG.md).
- Lavoro in corso: [ROADMAP.md](ROADMAP.md) (ciclo attuale) e [PROGETTO.md](PROGETTO.md) (dossier), generati
  dalla governance del progetto.

## Documentazione

L'indice completo è in [docs/README.md](docs/README.md).

| Documento | Contenuto |
|---|---|
| [PRINCIPI.md](PRINCIPI.md) | Principi, visione e decisioni prese |
| [docs/architettura.md](docs/architettura.md) | Studio dell'architettura agent-first: strati del sistema, presupposti umani, proposte |
| [docs/hardware.md](docs/hardware.md) | La Steam Deck: componenti, dischi, rete, limiti noti |
| [docs/chiavetta-live.md](docs/chiavetta-live.md) | Chiavetta di avvio con Wi-Fi e SSH automatici, anche per il recupero |
| [docs/installazione.md](docs/installazione.md) | Installazione di Arch a fasi e configurazione del sistema |
| [docs/accesso.md](docs/accesso.md) | Come l'agente raggiunge la Deck, sicurezza e recupero |
| [docs/protocollo.md](docs/protocollo.md) | Protocollo dell'interfaccia agentica: schermate, azioni, conferme, autoprompting |
| [docs/deck.md](docs/deck.md) | Il motore `deck`: uso, server MCP, codice, installazione, nuovi componenti |
| [docs/brain.md](docs/brain.md) | Il Brain: la memoria dell'agente (`brain`), ricerca, revisioni, collegamenti |
| [docs/segreti.md](docs/segreti.md) | Segreti del proprietario consegnati con un link monouso nella rete di casa (`deck secret`) |
| [docs/adattatore.md](docs/adattatore.md) | L'adattatore dei programmi interattivi (`deck term`) e i profili |
| [docs/obblighi.md](docs/obblighi.md) | Gli obblighi che il sistema dà all'agente (`deck obligations`) |
| [docs/servizi.md](docs/servizi.md) | L'area dei servizi ospitati dalla Deck (`/srv/servizi`) |
| [docs/claude-code.md](docs/claude-code.md) | Claude Code sulla Deck: installazione verificata, percorsi, aggiornamenti |
| [docs/sviluppo.md](docs/sviluppo.md) | Repository, versioni, pubblicazione su GitHub, governance |

## Struttura del repository

```
README.md        questa pagina
PRINCIPI.md      principi del progetto
CHANGELOG.md     storia delle versioni
VERSION          versione corrente
PROGETTO.md      dossier di progetto (generato dalla governance)
ROADMAP.md       roadmap del ciclo in corso (generata dalla governance)
docs/            documentazione per argomento
deck/            il comando deck: motore del protocollo, componenti, test, installazione
live/            chiavetta di avvio: preparazione dal Mac e script eseguito sulla Deck
install/         installazione di Arch sulla Deck e rifinitura dopo il primo avvio
servizi/         area dei servizi ospitati: unità modello e script (docs/servizi.md)
secrets/         credenziali locali, escluse da git (es. Wi-Fi)
cache/           ISO e file scaricati, esclusi da git
```
