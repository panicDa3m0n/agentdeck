<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Si aggiorna SOLO con i comandi wf.sh (project-set, roadmap-new, roadmap-archive). -->

# PROGETTO — linuxai-steamdeck

## Descrizione

AgentDeck: una Steam Deck LCD (APU AMD, 16 GB RAM, NVMe 2 TB) trasformata in server domestico a basso consumo con Arch Linux, progettato agent-first: il sistema è gestito interamente da un agente AI (oggi Claude, via SSH dal Mac) e l’umano è al massimo spettatore. Serve a ospitare servizi, applicazioni personali e domestiche, progetti di sviluppo e uso agentico completo. Ogni componente del sistema, prendendo spunto dalle funzioni di macOS, viene riprogettato per l’uso agentico con due tecnologie: interattività (ogni risposta è una schermata in JSON strutturato con dati, azioni, navigazione, errori e conferme come anteprima delle conseguenze) e autoprompting (il sistema fornisce all’agente le istruzioni giuste per il contesto in cui si trova). L’agente che sviluppa è anche l’agente che usa il sistema, così i bisogni emergono dall’uso reale. Obiettivo finale: agente interno basato su API cloud, idealmente sessioni Claude Code integrate nativamente con il sistema. Progetto personale di Davide. Nel repository: principi (PRINCIPI.md), chiavetta live con Wi-Fi e SSH automatici (live/), installazione di Arch a fasi (install/).

**Come si verifica che funziona:** La Deck si riavvia da sola dal disco interno e torna raggiungibile con ssh agentdeck (utente agent, solo chiave); systemctl is-system-running risponde running senza unità fallite; è attivo il kernel principale; snapper elenca gli snapshot e GRUB li rende avviabili. Gli script hanno controlli in sola lettura: install.sh check e verify, prepare-stick.sh con DRY_RUN=1. Non esistono ancora test automatici: ogni componente nuovo si verifica usandolo davvero come agente sulla Deck e controllando che la risposta sia JSON valido e coerente con lo stato reale.

**Versioni:** Il numero è MAJOR.MINOR.PATCH: il terzo sale a ogni task completata, qualunque sia il suo obiettivo; il secondo a ogni ciclo chiuso; il primo solo col sì dell'utente, su proposta dell'agente. Versione attuale: 0.2.2; il numero sta in VERSION. Ogni versione si pubblica appena chiusa.

## Dettagli

| Voce | Valore | Origine |
|---|---|---|
| ambiente | Steam Deck LCD a casa, sempre accesa e alimentata, in Wi-Fi sulla LAN domestica (192.168.1.0/24), raggiungibile come agentdeck.local con IP stabile 192.168.1.49; Arch Linux con kernel linux e linux-lts. Sviluppo dal MacBook Pro (repository in /Users/snj/linuxai-steamdeck), installazione e gestione via SSH. Repository privato su GitHub panicDa3m0n/agentdeck, ogni versione pubblicata con tag. | configurato |
| branch | main | rilevato |
| scopo_utente | Lo usano agenti AI (oggi Claude via SSH dal Mac, in futuro un agente interno su API cloud) per gestire servizi, ospitare applicazioni personali e domestiche, progetti di sviluppo e lavoro agentico; Davide è proprietario e spettatore, non operatore. | configurato |
| vincoli | Arch Linux; principio agent-first (PRINCIPI.md) e sviluppo incrementale con ogni intervento discusso prima; priorità alla velocità; interfaccia grafica necessaria ma solo come canale verso l'umano; niente cifratura del disco; microSD da 1 TB per ora intoccata; agente interno solo su API cloud, niente modelli locali; progetto personale: per GitHub si usa l'account panicDa3m0n; nessuna scadenza. | configurato |

## Cicli di sviluppo

### `01` Prima interfaccia agentica: protocollo, stato e snapshot — concluso il 2026-10-25 19:01

- Roadmap archiviata: [01-prima-interfaccia-agentica-protocollo-st.md](.claude/workflow/roadmaps/01-prima-interfaccia-agentica-protocollo-st.md)
- Aperto il 2026-10-25 15:54 · concluso il 2026-10-25 19:01
- **Risultato:** 3 obiettivi, 12 task completate, 0 rimaste bloccate
  - `O1` Base operativa affidabile per l'agente — approvato
    • O1.T1: Autore personale su tutti i commit; repo privato panicDa3m0n/agentdeck con main e tag v0.1.0, verificato via API; nessuna credenziale online.
    • O1.T2: SendRelease=no sulla Deck e in install.sh; snapshot 4 prima; dopo 2 riavvii consecutivi IP sempre .49; ssh agentdeck riuscito 5 volte su 5 al primo tentativo.
    • O1.T3: inetutils installato con pacman (snapshot pre 5 e post 6 da snap-pac); hostname restituisce agentdeck; pacchetto aggiunto a install/install.sh.
    • O1.T4: README, indice docs/ e 5 documenti; PRINCIPI con INV-10; 57 link verificati senza rotture; script e documenti collegati a vicenda; tutto su origin/main.
    • O1.T5: ssh agentdeck usa l'IP stabile .49 (HostKeyAlias), alias agentdeck-mdns sul nome; backup fatto; 10 collegamenti su 10 al primo colpo; accesso.md aggiornato.
  - `O2` Protocollo dell'interfaccia agentica: schermate interattive e autoprompting — approvato
    • O2.T1: docs/protocollo.md approvato: schermate, azioni, conferme, errori, autoprompting, INV-4, 8 esempi reali; Python 3, testi in inglese.
    • O2.T2: deck sulla Deck: home con componenti, errori strutturati, 8 chiamate reali conformi, 22 test verdi, ~0,09 s; install.sh ripetuto con successo.
  - `O3` Primi componenti usati dall'agente: stato del sistema e snapshot — approvato
    • O3.T1: deck status sulla Deck: 23/23 valori coincidono con gli strumenti classici, avvisi WIFI_BAND_2G, LLMNR, ventola; 34 test verdi; 0,27 s.
    • O3.T2: deck snapshot: elenco identico a snapper (1-13), snapshot 14 creato da deck in snapper e nel menu GRUB dopo 7 s; in_grub; 56 test.
    • O3.T3: Rollback provato: snap 15, modifica di prova, anteprima, conferma, Deck tornata in 44 s senza la modifica; stato prima nello snap 18; 67 test.
    • O3.T4: Schermo Deck: comandi agente ed esiti deck in tempo reale (verificato da /dev/vcsu1); snapshot 10; ssh, scp, rsync ok; docs/schermo.md.
    • O3.T5: Schermo: comando e risposta (errori in rosso, deck riassunto); I/O, uscite e binari invariati verificati; rete di sicurezza estesa; 48 test.

### `02` La Deck come server gestito dall'agente: rete, servizi, aggiornamenti, schermo — **in corso**

- Roadmap: [ROADMAP.md](ROADMAP.md)
- Aperto il 2026-10-25 19:02 · ultimo aggiornamento 2026-10-25 19:51

## Debito ereditato

_nessun debito aperto._
