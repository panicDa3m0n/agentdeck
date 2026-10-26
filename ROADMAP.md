<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 05: Il sistema è dell'agente: permessi, servizi e repository

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** —
- **Task attiva:** —
- **Ultima task gestita:** —
- **Ultimo aggiornamento:** 2026-10-26 11:38

## Richieste attive

_nessuna richiesta in attesa._

## Obiettivi

### `O12` L'agente lavora su AgentDeck senza chiedere permessi (ADR-0001), con più protezione — in corso

**Gate obiettivo:** In una sessione reale con Remote Control l'agente interviene sul sistema senza richieste di permesso e chiede solo per i dati e i singoli servizi dell'utente; i vincoli che proteggono l'accesso (INV-1) e le anteprime di deck restano; sshguard protetto come l'accesso; snapshot prima di ogni modifica rischiosa (INV-3).

- [ ] `O12.T1` Politica dei permessi ADR-0001 nelle impostazioni gestite e nelle regole dell'agente (N46) — *perimetro:* `deck/claude/, deck/tests/, docs/, /etc/claude-code sulla Deck`
  *gate previsto:* Impostazioni gestite che permettono tutto il lavoro di sistema senza richieste e chiedono solo per i dati dell'utente e i singoli servizi dell'utente; deny e guardia dell'accesso invariati; le frasi che fanno chiedere al proprietario modifiche di sistema tolte da CLAUDE.md, guardia e skill; provato con claude -p sulla Deck senza permessi aggiuntivi: comandi di sistema senza richieste, dati dell'utente con richiesta; test; documentazione.
- [ ] `O12.T2` sshguard protetto come l'accesso: regole, guardia e avviso di deck status (N42) — *perimetro:* `deck/, docs/, /etc/claude-code sulla Deck`
  *gate previsto:* Le regole dell'agente dicono che sshguard non si ferma e la sua whitelist non si allarga; guardia e deny rifiutano stop, disable e mask di sshguard; deck status avvisa se sshguard non è attivo; test; documentazione.
- [ ] `O12.T3` Il cambio di Wi-Fi ritenta prima di tornare indietro (N49) — *perimetro:* `deck/, docs/`
  *gate previsto:* wifi_switch ritenta la connessione alla rete nuova dopo qualche secondo prima di tornare alla precedente; ritorno automatico invariato; test; prova dal vivo con ssh agentdeck sempre funzionante (INV-1); documentazione.
- [ ] `O12.T4` Pacchetti dell'installazione allineati alla Deck: tmux e sshguard in install/install.sh (N28) — *perimetro:* `install/, docs/`
  *gate previsto:* install/install.sh installa anche tmux e sshguard, come oggi la Deck; sintassi verificata; documentazione di installazione aggiornata.
- [ ] `O12.T5` Sessione reale con Remote Control: permessi e strumenti nuovi (N54) — *perimetro:* `sessioni di Claude Code sulla Deck, annotazioni, docs/`
  *gate previsto:* Una sessione reale scelta con l'utente, seguita con Remote Control: nessuna richiesta di permesso per il lavoro di sistema; uso di deck mcp, adattatore, obblighi e skill osservato nel registro delle sessioni; bisogni emersi annotati.

### `O13` I servizi della Deck gestiti dal sistema (N53) — in corso

**Gate obiettivo:** L'agente crea, aggiorna e rimuove un servizio vero con deck servizi, con anteprime e snapshot dei dati; dalla rete di casa passano solo SSH e le porte dei servizi esposti per decisione dell'utente; ssh agentdeck sempre funzionante (INV-1).

- [ ] `O13.T1` deck servizi: elenco, crea, aggiorna da git, rimuovi con anteprima; area dei servizi nelle regole dell'agente (N53, N56) — *perimetro:* `deck/, servizi/, docs/`
  *gate previsto:* deck servizi elenca le cartelle di /srv/servizi con lo stato dell'unità, anche ferma; crea, aggiorna da git e rimuove un servizio con anteprima e conferma; le azioni su un servizio dell'utente seguono ADR-0001; CLAUDE.md cita l'area dei servizi; INV-4; test; documentazione.
- [ ] `O13.T2` Snapshot dei dati dei servizi: configurazione snapper per @servizi (N53) — *perimetro:* `deck/, servizi/, docs/, configurazione snapper sulla Deck`
  *gate previsto:* Configurazione snapper servizi per @servizi; deck servizi fa uno snapshot dei dati prima di aggiornare o rimuovere un servizio; ritorno a uno snapshot dei dati provato su un servizio di prova; documentazione.
- [ ] `O13.T3` Firewall nftables con rete di sicurezza che si annulla da sola (N53) — *perimetro:* `deck/, servizi/, docs/, nftables sulla Deck`
  *gate previsto:* Dalla LAN passano solo SSH e le porte dei servizi esposti per decisione dell'utente; la regola si applica con una rete di sicurezza che la toglie da sola se ssh agentdeck non viene confermato; ssh agentdeck da LAN e da internet funzionante dopo; documentazione.
- [ ] `O13.T4` Il primo servizio vero, scelto dall'utente — *perimetro:* `/srv/servizi sulla Deck, docs/`
  *gate previsto:* Un servizio scelto dall'utente installato e avviato con deck servizi nell'area dei servizi, seguito dall'agente; aggiornamento e ritorno indietro provati; documentazione del servizio nel suo LEGGIMI.md.

### `O14` Quello che l'agente fa sulla Deck arriva nel repository (N52) — in corso

**Gate obiettivo:** Una modifica di sistema fatta dall'agente sulla Deck finisce in git e in docs/ senza che una sessione dal Mac la copi a mano; nessuna credenziale nel repository (INV-6); versione pubblicata (INV-8).

- [ ] `O14.T1` Il canale fra l'agente sulla Deck e il repository, deciso con l'utente (N52) — *perimetro:* `docs/, decisioni`
  *gate previsto:* Strade confrontate con l'utente (copia del repository sulla Deck con push e credenziale solo sulla Deck, consegna verso il Mac, stato voluto D4); decisione registrata come ADR.
- [ ] `O14.T2` Il canale realizzato e provato con una modifica vera dell'agente sulla Deck — *perimetro:* `deck/, docs/, configurazione sulla Deck`
  *gate previsto:* Una modifica vera fatta da una sessione sulla Deck arriva nel repository secondo il canale deciso, con documentazione e versione pubblicata; nessuna credenziale in git (INV-6).

## Annotazioni

_nessuna annotazione._
