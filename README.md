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
- `deck`, l'interfaccia di sistema per agenti, installata sulla Deck: `ssh agentdeck deck`
  (vedi [docs/deck.md](docs/deck.md) e il protocollo in [docs/protocollo.md](docs/protocollo.md)).
- Lo schermo della Deck mostra, come un terminale, ogni comando dell'agente e l'esito di `deck`
  (vedi [docs/schermo.md](docs/schermo.md)).
- Versione corrente nel file [VERSION](VERSION); storia delle versioni in [CHANGELOG.md](CHANGELOG.md).
- Lavoro in corso: [ROADMAP.md](ROADMAP.md) (ciclo attuale) e [PROGETTO.md](PROGETTO.md) (dossier), generati
  dalla governance del progetto.

## Documentazione

L'indice completo è in [docs/README.md](docs/README.md).

| Documento | Contenuto |
|---|---|
| [PRINCIPI.md](PRINCIPI.md) | Principi, visione e decisioni prese |
| [docs/hardware.md](docs/hardware.md) | La Steam Deck: componenti, dischi, rete, limiti noti |
| [docs/chiavetta-live.md](docs/chiavetta-live.md) | Chiavetta di avvio con Wi-Fi e SSH automatici, anche per il recupero |
| [docs/installazione.md](docs/installazione.md) | Installazione di Arch a fasi e configurazione del sistema |
| [docs/accesso.md](docs/accesso.md) | Come l'agente raggiunge la Deck, sicurezza e recupero |
| [docs/protocollo.md](docs/protocollo.md) | Protocollo dell'interfaccia agentica: schermate, azioni, conferme, autoprompting |
| [docs/deck.md](docs/deck.md) | Il motore `deck`: uso, codice, installazione, nuovi componenti |
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
secrets/         credenziali locali, escluse da git (es. Wi-Fi)
cache/           ISO e file scaricati, esclusi da git
```
