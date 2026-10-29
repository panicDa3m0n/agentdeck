<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Si aggiorna SOLO con i comandi wf.sh (project-set, roadmap-new, roadmap-archive). -->

# PROGETTO — linuxai-steamdeck

## Descrizione

AgentDeck: una Steam Deck LCD (APU AMD, 16 GB RAM, NVMe 2 TB) trasformata in server domestico a basso consumo con Arch Linux, progettato agent-first: il sistema è gestito interamente da un agente AI (oggi Claude, via SSH dal Mac) e l’umano è al massimo spettatore. Serve a ospitare servizi, applicazioni personali e domestiche, progetti di sviluppo e uso agentico completo. Ogni componente del sistema, prendendo spunto dalle funzioni di macOS, viene riprogettato per l’uso agentico con due tecnologie: interattività (ogni risposta è una schermata in JSON strutturato con dati, azioni, navigazione, errori e conferme come anteprima delle conseguenze) e autoprompting (il sistema fornisce all’agente le istruzioni giuste per il contesto in cui si trova). L’agente che sviluppa è anche l’agente che usa il sistema, così i bisogni emergono dall’uso reale. Obiettivo finale: agente interno basato su API cloud, idealmente sessioni Claude Code integrate nativamente con il sistema. Progetto personale di Davide. Nel repository: principi (PRINCIPI.md), chiavetta live con Wi-Fi e SSH automatici (live/), installazione di Arch a fasi (install/).

**Come si verifica che funziona:** La Deck si riavvia da sola dal disco interno e torna raggiungibile con ssh agentdeck (utente agent, solo chiave); systemctl is-system-running risponde running senza unità fallite; è attivo il kernel principale; snapper elenca gli snapshot e GRUB li rende avviabili. Gli script hanno controlli in sola lettura: install.sh check e verify, prepare-stick.sh con DRY_RUN=1. Non esistono ancora test automatici: ogni componente nuovo si verifica usandolo davvero come agente sulla Deck e controllando che la risposta sia JSON valido e coerente con lo stato reale.

**Versioni:** Il numero è MAJOR.MINOR.PATCH: il terzo sale a ogni task completata, qualunque sia il suo obiettivo; il secondo a ogni ciclo chiuso; il primo solo col sì dell'utente, su proposta dell'agente. Versione attuale: 0.5.4; il numero sta in VERSION. Ogni versione si pubblica appena chiusa.

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

### `02` La Deck come server gestito dall'agente: rete, servizi, aggiornamenti, schermo — concluso il 2026-10-25 20:23

- Roadmap archiviata: [02-la-deck-come-server-gestito-dall-agente-.md](.claude/workflow/roadmaps/02-la-deck-come-server-gestito-dall-agente-.md)
- Aperto il 2026-10-25 19:02 · concluso il 2026-10-25 20:23
- **Risultato:** 4 obiettivi, 4 task completate, 3 rimaste bloccate
  - `O4` Rete gestita dall'agente: deck network — approvato
    • O4.T1: deck network: 11/11 valori uguali a ip, iw, resolvectl, ss; rete sorella a 5 GHz riconosciuta; avvisi di status puntano a /network; 80 test.
    • O4.T2: deck network: llmnr_off/on e prefer_5ghz con ritorno automatico, provati dal vivo; Deck sui 5 GHz anche dopo riavvio, ssh ok, 11/11, 100 test
  - `O5` Servizi e log gestiti dall'agente: deck service, deck logs — approvato
    • O5.T1: deck service: elenco come systemctl, azioni su servizio di prova con anteprima e snapshot, stop e disable dei 5 servizi di accesso rifiutati; 28/28, 122 test
    • O5.T2: deck logs: filtri per unità, periodo, gravità uguali a journalctl -o json, traccia agente esclusa, riga malevola solo nei dati, link da service; 11/11, 134 test
  - `O6` Aggiornamenti sicuri: deck update — deck update pronto e installato; manca la prova con un aggiornamento vero di Arch, da fare al primo disponibile (decisione dell'utente)
  - `O7` Schermo leggibile e compatto, sistema pulito: deck screen — Rinviato dall'utente a dopo lo studio dell'architettura agent-first: schermo compatto e pulizia passano come debito al ciclo 03

### `03` Studio dell'architettura agent-first: come funziona il sistema e dove intercettarlo — concluso il 2026-10-25 23:47

- Roadmap archiviata: [03-studio-dell-architettura-agent-first-com.md](.claude/workflow/roadmaps/03-studio-dell-architettura-agent-first-com.md)
- Aperto il 2026-10-25 20:24 · concluso il 2026-10-25 23:47
- **Risultato:** 2 obiettivi, 7 task completate, 1 rimaste bloccate
  - `O8` Mappa del sistema e architettura agent-first — approvato
    • O8.T1: Sezione 1 di architettura.md: avvio misurato (20 s), 8 presupposti umani (root bloccato in emergenza, panic, watchdog spento), 11 proposte
    • O8.T2: Sezione 2 di architettura.md: 18 socket varlink e D-Bus misurati (8 ms), deck usa 12 parser di testo; 6 presupposti umani, 7 proposte
    • O8.T3: Sezione 3 di architettura.md: sudo ALL senza polkit, nessuna sandbox né audit né firewall, TPM e Landlock pronti; 6 presupposti umani, 8 proposte
    • O8.T4: Sezione 4 di architettura.md: 32 snapshot (19 senza pulizia), configurazione imperativa in 24 file, sysext e nspawn pronti; 5 presupposti umani, 8 proposte
    • O8.T5: Sezione 5 di architettura.md: journal (28% traccia agente, 42% eventi riconoscibili), sistema silenzioso, nessuno sveglia l'agente; 5 presupposti, 9 proposte
    • O8.T6: Sezione 6 di architettura.md: fork di Claude Code non permesso (licenza), Agent SDK, hook, MCP, Remote Control verificati; dove vivono le sessioni; 6 proposte
    • O8.T7: Sintesi e revisione: Claude Code come harness, il sistema guida l'agente, adattatore dei prompt, obblighi come avvisi, si parte da Claude Code sulla Deck
  - `O9` Aggiornamento reale della Deck con deck update — deck update pronto; manca ancora la prova con un aggiornamento vero di Arch, rinviata al ciclo 04

### `04` Claude Code dentro AgentDeck: installazione, configurazione e uso reale — concluso il 2026-10-26 11:35

- Roadmap archiviata: [04-claude-code-dentro-agentdeck-installazio.md](.claude/workflow/roadmaps/04-claude-code-dentro-agentdeck-installazio.md)
- Aperto il 2026-10-25 23:48 · concluso il 2026-10-26 11:35
- **Risultato:** 2 obiettivi, 11 task completate, 2 rimaste bloccate
  - `O10` Claude Code sulla Deck, usato davvero — Approvato dall'utente il 26/10. Claude Code sulla Deck usato davvero: abbonamento, Remote Control, deck mcp, adattatore, obblighi, hook, skill; accesso da fuori casa verificato in O10.T10, che supera O10.T5 rimasta bloccata; sessione reale con l'area dei servizi portata nel repository.
    • O10.T1: Claude Code 2.1.310 sulla Deck per agent: firma GPG del manifest e checksum verificate, --version e doctor ok, nessuna porta nuova; install/claude-code.sh
    • O10.T2: Login Max, token solo sulla Deck; claude -p ok; servizio con Remote Control in tmux, riconnesso dopo riavvio; sessione vista dall'utente
    • O10.T3: Prompt di sistema in quattro strati (stile, CLAUDE.md gestito, deny e guardia, hook con gli avvisi); provati con claude -p e da Remote Control dall'utente
    • O10.T4: Sessione reale del 26/10: area dei servizi preparata dall'agente e verificata; bisogni N51-N54 annotati; proposta del ciclo 05
    • O10.T6: deck mcp: open più 18 strumenti tipizzati, risorse, conferme in due passi; provato da claude -p sulla Deck e via ssh dal Mac; 172 test
    • O10.T7: deck term: programmi in tmux come schermate, segreti rifiutati, guardia; 20/20 dal vivo; profilo ssh-keygen scritto dall'agente
    • O10.T8: deck obligations e hook: obbligo dall'hook di pacman, campo obligations, politica, verifiche, novità del turno, registro; provati dal vivo
    • O10.T9: 6 skill di AgentDeck installate; prova d'insieme: tree installato da sola con skill, MCP, adattatore e obbligo chiuso; 229 test
    • O10.T10: Accesso da fuori casa verificato dall'hotspot: ssh agentdeck via scarlethome.ddns.net:49222, deck status, deck/install.sh; IP esterno vero
    • O10.T11: Deck di nuovo a 5 GHz (5180 MHz) con prefer_5ghz e keep_5ghz al secondo tentativo; IP invariato, ssh ok, WIFI_BAND_2G sparito
    • O10.T12: Area dei servizi nel repository (servizi/, docs/servizi.md), identica all'installato per checksum; collegata da indice, deck.md, installazione
  - `O11` Aggiornamento reale della Deck con deck update (O9) — Rimandato su decisione dell'utente (26/10): la prova di deck update si fa solo quando l'utente la chiederà; resta nel debito, da tralasciare fino ad allora.

### `05` Il sistema è dell'agente: permessi, servizi e repository — **in corso**

- Roadmap: [ROADMAP.md](ROADMAP.md)
- Aperto il 2026-10-26 11:36 · ultimo aggiornamento 2026-10-29 21:45

## Debito ereditato

_nessun debito aperto._
