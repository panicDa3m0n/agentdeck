<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Si aggiorna SOLO con i comandi wf.sh (project-set, roadmap-new, roadmap-archive). -->

# PROGETTO — linuxai-steamdeck

## Descrizione

AgentDeck: una Steam Deck LCD (APU AMD, 16 GB RAM, NVMe 2 TB) trasformata in server domestico a basso consumo con Arch Linux, progettato agent-first: il sistema è gestito interamente da un agente AI (oggi Claude, via SSH dal Mac) e l’umano è al massimo spettatore. Serve a ospitare servizi, applicazioni personali e domestiche, progetti di sviluppo e uso agentico completo. Ogni componente del sistema, prendendo spunto dalle funzioni di macOS, viene riprogettato per l’uso agentico con due tecnologie: interattività (ogni risposta è una schermata in JSON strutturato con dati, azioni, navigazione, errori e conferme come anteprima delle conseguenze) e autoprompting (il sistema fornisce all’agente le istruzioni giuste per il contesto in cui si trova). L’agente che sviluppa è anche l’agente che usa il sistema, così i bisogni emergono dall’uso reale. Obiettivo finale: agente interno basato su API cloud, idealmente sessioni Claude Code integrate nativamente con il sistema. Progetto personale di Davide. Nel repository: principi (PRINCIPI.md), chiavetta live con Wi-Fi e SSH automatici (live/), installazione di Arch a fasi (install/).

**Come si verifica che funziona:** La Deck si riavvia da sola dal disco interno e torna raggiungibile con ssh agentdeck (utente agent, solo chiave); systemctl is-system-running risponde running senza unità fallite; è attivo il kernel principale; snapper elenca gli snapshot e GRUB li rende avviabili. Gli script hanno controlli in sola lettura: install.sh check e verify, prepare-stick.sh con DRY_RUN=1. Non esistono ancora test automatici: ogni componente nuovo si verifica usandolo davvero come agente sulla Deck e controllando che la risposta sia JSON valido e coerente con lo stato reale.

**Versioni:** Il numero è MAJOR.MINOR.PATCH: il terzo sale a ogni task completata, qualunque sia il suo obiettivo; il secondo a ogni ciclo chiuso; il primo solo col sì dell'utente, su proposta dell'agente. Versione attuale: 0.1.8; il numero sta in VERSION. Ogni versione si pubblica appena chiusa.

## Dettagli

| Voce | Valore | Origine |
|---|---|---|
| ambiente | Steam Deck LCD a casa, sempre accesa e alimentata, in Wi-Fi sulla LAN domestica (192.168.1.0/24), raggiungibile come agentdeck.local con IP stabile 192.168.1.49; Arch Linux con kernel linux e linux-lts. Sviluppo dal MacBook Pro (repository in /Users/snj/linuxai-steamdeck), installazione e gestione via SSH. Repository privato su GitHub panicDa3m0n/agentdeck, ogni versione pubblicata con tag. | configurato |
| branch | main | rilevato |
| scopo_utente | Lo usano agenti AI (oggi Claude via SSH dal Mac, in futuro un agente interno su API cloud) per gestire servizi, ospitare applicazioni personali e domestiche, progetti di sviluppo e lavoro agentico; Davide è proprietario e spettatore, non operatore. | configurato |
| vincoli | Arch Linux; principio agent-first (PRINCIPI.md) e sviluppo incrementale con ogni intervento discusso prima; priorità alla velocità; interfaccia grafica necessaria ma solo come canale verso l'umano; niente cifratura del disco; microSD da 1 TB per ora intoccata; agente interno solo su API cloud, niente modelli locali; progetto personale: per GitHub si usa l'account panicDa3m0n; nessuna scadenza. | configurato |

## Cicli di sviluppo

### `01` Prima interfaccia agentica: protocollo, stato e snapshot — **in corso**

- Roadmap: [ROADMAP.md](ROADMAP.md)
- Aperto il 2026-10-25 15:54 · ultimo aggiornamento 2026-10-25 17:48

## Debito ereditato

_nessun debito aperto._
