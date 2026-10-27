<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 05: Il sistema è dell'agente: permessi, servizi e repository

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** `O15` Interfacce effimere sullo schermo della Deck: lo stile e la prima interfaccia, le sessioni Claude — 3 task: 1 completate, 0 in corso, 2 da fare, 0 bloccate
- **Task attiva:** —
- **Ultima task gestita:** `O15.T1` — completata — Stile (7 regole) e grafica cage+Chromium decisi con l'utente: ADR-0003 accettato, docs/interfacce.md nell'indice, link verificati
- **Ultimo aggiornamento:** 2026-10-27 22:47

## Richieste attive

_nessuna richiesta in attesa._

## Obiettivi

### `O12` L'agente lavora su AgentDeck senza chiedere permessi (ADR-0001), con più protezione — in corso

**Gate obiettivo:** In una sessione reale con Remote Control l'agente interviene sul sistema senza richieste di permesso e chiede solo per i dati e i singoli servizi dell'utente; i vincoli che proteggono l'accesso (INV-1) e le anteprime di deck restano; sshguard protetto come l'accesso; snapshot prima di ogni modifica rischiosa (INV-3).
**Documenti:** `ADR-0002`

- [!] `O12.T1` Politica dei permessi ADR-0001 nelle impostazioni gestite e nelle regole dell'agente (N46) — *perimetro:* `deck/claude/, deck/tests/, docs/, /etc/claude-code sulla Deck, deck/agentdeck/ownership.py e il prompt della guardia in deck/agentdeck/components/term.py`
  *gate previsto:* Impostazioni gestite che permettono tutto il lavoro di sistema senza richieste e chiedono solo per i dati dell'utente e i singoli servizi dell'utente; deny e guardia dell'accesso invariati; le frasi che fanno chiedere al proprietario modifiche di sistema tolte da CLAUDE.md, guardia e skill; provato con claude -p sulla Deck senza permessi aggiuntivi: comandi di sistema senza richieste, dati dell'utente con richiesta; test; documentazione. · *blocco:* ✖ Politica pronta e provata sul Mac (241 test); manca l'installazione: riavvia agentdeck-claude e chiuderebbe la sessione su frugale
  *rischio:* 30/100 — Cambia cosa l'agente fa senza chiedere: un errore toccherebbe un servizio o una credenziale dell'utente senza permesso o fermerebbe lavoro legittimo. Deny e guardia dell'accesso invariati; l'installazione riavvia agentdeck-claude, quindi si fa a sessione finita.
  *annotazioni:* `N58`, `N59`, `N63`
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
  *annotazioni:* `N64`
- [ ] `O13.T2` Snapshot dei dati dei servizi: configurazione snapper per @servizi (N53) — *perimetro:* `deck/, servizi/, docs/, configurazione snapper sulla Deck`
  *gate previsto:* Configurazione snapper servizi per @servizi; deck servizi fa uno snapshot dei dati prima di aggiornare o rimuovere un servizio; ritorno a uno snapshot dei dati provato su un servizio di prova; documentazione.
- [ ] `O13.T3` Firewall nftables con rete di sicurezza che si annulla da sola (N53) — *perimetro:* `deck/, servizi/, docs/, nftables sulla Deck`
  *gate previsto:* Dalla LAN passano solo SSH e le porte dei servizi esposti per decisione dell'utente; la regola si applica con una rete di sicurezza che la toglie da sola se ssh agentdeck non viene confermato; ssh agentdeck da LAN e da internet funzionante dopo; documentazione.
- [ ] `O13.T4` Il primo servizio vero, scelto dall'utente — *perimetro:* `/srv/servizi sulla Deck, docs/`
  *gate previsto:* Un servizio scelto dall'utente installato e avviato con deck servizi nell'area dei servizi, seguito dall'agente; aggiornamento e ritorno indietro provati; documentazione del servizio nel suo LEGGIMI.md.

### `O14` Quello che l'agente fa sulla Deck arriva nel repository (N52) — chiuso

**Gate obiettivo:** Una modifica di sistema fatta dall'agente sulla Deck finisce in git e in docs/ senza che una sessione dal Mac la copi a mano; nessuna credenziale nel repository (INV-6); versione pubblicata (INV-8).
**Chiuso:** 2026-10-27 21:36 — approvato dall'utente: la Deck pubblica da sé su GitHub (ADR-0002), provato con frugale (58 commit), v0.5.2

- [x] `O14.T1` Il canale fra l'agente sulla Deck e il repository, deciso con l'utente (N52) — *perimetro:* `docs/, decisioni`
  *gate previsto:* Strade confrontate con l'utente (copia del repository sulla Deck con push e credenziale solo sulla Deck, consegna verso il Mac, stato voluto D4); decisione registrata come ADR. · *gate confermato:* ✔ Canale deciso dall'utente (ADR-0002): la Deck pubblica da sé su GitHub come panicDa3m0n, login gh approvato dall'utente, repository privati
  *rischio:* 5/100 — Solo la registrazione della decisione dell'utente sul canale: nessuna modifica al sistema.
  *annotazioni:* `N60`
- [x] `O14.T2` Il canale realizzato e provato con una modifica vera dell'agente sulla Deck — *perimetro:* `pacchetto github-cli e configurazione di gh e git dell'utente agent sulla Deck, remote di /home/agent/frugale sulla Deck, deck/, docs/`
  *gate previsto:* Una modifica vera fatta da una sessione sulla Deck arriva nel repository secondo il canale deciso, con documentazione e versione pubblicata; nessuna credenziale in git (INV-6). · *gate confermato:* ✔ frugale pubblicato dalla Deck (gh panicDa3m0n): 58 commit fino a 8fa5cbd, push nel reflog della Deck, 0 credenziali; docs e regola
  *rischio:* 25/100 — Pacchetto nuovo e credenziale dell'account personale sulla Deck esposta via SSH (solo chiave): il token apre i repository personali. Snapshot prima, nessun riavvio di agentdeck-claude, nessun file di lavoro di frugale toccato.
  *annotazioni:* `N61`, `N62`

### `O15` Interfacce effimere sullo schermo della Deck: lo stile e la prima interfaccia, le sessioni Claude — in corso

**Gate obiettivo:** Lo schermo della Deck, al posto del terminale, resta calmo e mostra un'interfaccia grafica effimera solo quando serve; con il tocco o i pulsanti si vedono, si aprono e si chiudono le sessioni Claude; stile deciso come ADR e documentato; versione pubblicata.
**Documenti:** `ADR-0003`

- [x] `O15.T1` Lo stile delle interfacce effimere e la tecnologia grafica dello schermo, decisi con l'utente — *perimetro:* `docs/, PRINCIPI.md`
  *gate previsto:* Regole dello stile e tecnologia grafica (compositore e motore di pagina) confrontate e decise con l'utente, registrate come ADR-0003 e in docs/interfacce.md con l'indice. · *gate confermato:* ✔ Stile (7 regole) e grafica cage+Chromium decisi con l'utente: ADR-0003 accettato, docs/interfacce.md nell'indice, link verificati
  *rischio:* 15/100 — Solo documenti e una decisione; la decisione porta componenti grafici nuovi in T3 (INV-10), quindi va registrata come scelta esplicita dell'utente
  *documenti:* `ADR-0003`
- [ ] `O15.T2` La schermata deck claude: elencare, aprire e chiudere le sessioni Claude della Deck — *perimetro:* `deck/, docs/`
  *gate previsto:* deck claude elenca le sessioni con titolo e stato, ne apre una nuova che compare nell'app Claude e ne chiude una con anteprima e conferma, anche come strumenti MCP; test verdi; provato sulla Deck con una sessione di prova senza toccare quelle al lavoro.
- [ ] `O15.T3` Lo schermo grafico calmo con l'interfaccia effimera delle sessioni, al posto del terminale — *perimetro:* `deck/, docs/, pacchetti grafici e servizio dello schermo sulla Deck`
  *gate previsto:* Sulla Deck lo schermo grafico sostituisce il terminale: di base calmo, l'interfaccia delle sessioni compare con un tocco o un pulsante e sparisce dopo la scelta o il tempo; aprire e chiudere una sessione di prova funziona dal tocco; snapshot prima; ssh agentdeck intatto (INV-1); docs e versione pubblicata.

## Annotazioni

_Una riga per nota, sempre legata a una task. `wf.sh notes` per leggerle._

- `N58` (`O12.T1`) Precisazione dell'utente (26/10) su ADR-0001, cosa sono i dati dell'utente: i suoi servizi in /srv/servizi/<nome> (codice, configurazione, dati, segreti, avvio, arresto, abilitazione delle unità agentdeck-servizio@<nome>) e le sue credenziali (login di Claude, chiavi SSH). Sui progetti che l'utente chiede all'agente, come /home/agent/frugale, l'agente lavora libero. Vincolo di questo momento: una sessione di Remote Control sta lavorando a frugale; l'installazione sulla Deck riavvia agentdeck-claude e la chiuderebbe, quindi si installa solo quando l'utente dice che la sessione è finita. — 2026-10-26 17:56
- `N59` (`O12.T1`) Stato (26/10 18:00): politica pronta e provata sul Mac (agentdeck/ownership.py, guardia con permissionDecision ask, allow di tutto il lavoro di sistema nelle impostazioni gestite, testi senza richieste al proprietario per il sistema, 241 test). Non installata: sulla Deck è attiva la sessione di Remote Control su frugale (ultima attività 17:57) e deck/claude/install.sh riavvia agentdeck-claude. Restano installazione e prova con claude -p senza permessi aggiuntivi. — 2026-10-26 17:59
- `N60` (`O14.T1`) Caso reale (26/10, su richiesta dell'utente, fuori dal perimetro di O12.T1): pubblicato il progetto frugale nato sulla Deck, come chiede la sua decisione 0009. Repository privato panicDa3m0n/frugale; clone sul Mac in /Users/snj/frugale con remote deck (agentdeck:/home/agent/frugale) e origin HTTPS con credential helper locale di panicDa3m0n (come P1); push di main (de60013, bbe2177). Il ponte è manuale: per ogni aggiornamento serve git pull deck main e git push origin main dal Mac. È il bisogno N52 anche per i progetti dell'utente, non solo per AgentDeck. — 2026-10-26 18:20
- `N61` (`O14.T2`) Adattatore: nei menu a frecce (gh auth login) le opzioni sotto la riga del cursore non entrano in question.options; servirebbe una regola o un profilo per i menu a frecce (segnalato dall'agente della Deck il 26/10, scritto in docs/adattatore.md, Limiti noti) — 2026-10-26 18:53
- `N62` (`O14.T2`) Stato O14.T2 (26/10 18:56): nel repository pronti ownership con il login GitHub come credenziale, correzione Go dell'adattatore (P23), regola GitHub in CLAUDE.template.md, docs; risposta all'agente della Deck data all'utente. Manca la prova del gate: il push di frugale dalla Deck (origin ancora assente, 3 commit non pubblicati). Copia doppia /Users/snj/frugale/frugale spostata nel Cestino su richiesta dell'utente. — 2026-10-26 18:57
- `N63` (`O12.T1`) Sulla Deck (27/10): SendMessage aggiunto a permissions.allow di /etc/claude-code/managed-settings.json (copia .bak-sendmessage), su richiesta dell'utente: l'agente non deve aspettare un clic per scrivere a un'altra chat. Sulla Deck è installato ancora solo mcp__deck: tutta la politica ADR-0001 resta da installare; stessa voce nel repository e in docs/claude-code.md. Copiato anche il token Baxi nei segreti di domus (600, srv-domus), su richiesta dell'utente. — 2026-10-27 18:44
- `N64` (`O13.T1`) Servizio domus (27/10, su richiesta dell'utente dalla sessione della Deck): token Baxi copiato in /srv/servizi/domus/dati/secrets (600, srv-domus), /state funziona sulla Deck; motore Domus sul Mac (PID 35282, *:8777, avviato a mano, non da launchd) fermato con SIGINT, porta 8777 chiusa; resta sul Mac un'istanza di prova su 127.0.0.1:8778 (PID 46342), non toccata. — 2026-10-27 19:47
