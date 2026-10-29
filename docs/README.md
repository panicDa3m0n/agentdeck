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

- [piano.md](piano.md): il piano di sviluppo deciso con l'utente il 29/10/2026 (agente interno, approvazioni da
  agente ad agente, richieste, Brain, sviluppo sulla Deck, versioni fissate) e l'ordine di lavoro.
- [agente-interno.md](agente-interno.md): l'agente interno della Deck (MiniMax via Claude Code), l'intermediario
  locale che toglie l'identità Claude, configurazione, chiave e prove. Codice:
  [../deck/agentdeck/minimax_proxy.py](../deck/agentdeck/minimax_proxy.py).

## Architettura

- [architettura.md](architettura.md): studio dell'architettura agent-first del ciclo 03, strato per strato:
  come funziona il sistema, i presupposti umani, i punti di intercettazione e le proposte da decidere.

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
- [deck.md](deck.md): il motore di `deck`: uso, server MCP (`deck mcp`), codice, installazione, come aggiungere
  un componente. Codice: [../deck/](../deck/deck), [../deck/agentdeck/mcp.py](../deck/agentdeck/mcp.py).
- [adattatore.md](adattatore.md): l'adattatore dei programmi interattivi, `deck term`: un programma in tmux come
  schermata JSON, domande riconosciute, profili scritti dall'agente. Codice: [../deck/agentdeck/term.py](../deck/agentdeck/term.py).
- [obblighi.md](obblighi.md): gli obblighi che il sistema dà all'agente (`deck obligations`), dall'hook di pacman
  al campo `obligations` di ogni schermata. Codice: [../deck/agentdeck/obligations.py](../deck/agentdeck/obligations.py).
- [interfacce.md](interfacce.md): le interfacce effimere sullo schermo della Deck: le sette regole dello stile,
  la tecnologia grafica (cage + Chromium in kiosk, pagine locali di `deck`), la decisione ADR-0003, la schermata
  `deck claude` e lo schermo delle sessioni. Codice: [../deck/ui/](../deck/ui/index.html),
  [../deck/agentdeck/ui.py](../deck/agentdeck/ui.py).
- [schermo.md](schermo.md): lo schermo della Deck mostra, come un terminale, ogni comando dell'agente, la sua risposta e
  l'esito di `deck`. Codice: [../deck/screen/](../deck/screen/agentdeck_screen.py).

## Agenti

- [claude-code.md](claude-code.md): Claude Code sulla Deck, l'harness degli agenti: installazione verificata,
  percorsi, prompt di sistema in strati, strumenti MCP, hook di autoprompting, skill, aggiornamenti. Codice: [../install/claude-code.sh](../install/claude-code.sh).

## Uso quotidiano

- [servizi.md](servizi.md): l'area dei servizi ospitati dalla Deck (`/srv/servizi`): struttura, isolamento, rete,
  come si aggiunge e si gestisce un servizio. Codice: [../servizi/](../servizi/install-servizi.sh).

- [accesso.md](accesso.md): accesso SSH dell'agente in casa e da fuori casa (scarlethome.ddns.net, sshguard),
  indirizzo della Deck, sicurezza, snapshot e recupero. Codice: [../install/remote-access.sh](../install/remote-access.sh),
  prova da fuori casa [../install/remote-check.sh](../install/remote-check.sh).
- [sviluppo.md](sviluppo.md): repository git, identità, remote GitHub, pubblicazione dalla Deck con `gh` (ADR-0002),
  versioni, governance.
