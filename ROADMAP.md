<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 05: Il sistema è dell'agente: permessi, servizi e repository

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** `O20` L'agente interno di AgentDeck: MiniMax via Claude Code con un intermediario locale, identità AgentDeck (piano punto 1) — 3 task: 0 completate, 1 in corso, 2 da fare, 0 bloccate
- **Task attiva:** `O20.T1` Intermediario locale verso MiniMax: toglie la riga fissa Claude e adatta la richiesta — in corso · rischio 20/100
- **Ultima task gestita:** `O19.T2` — bloccata — Non sviluppata dall'agente in questa sessione: da rivedere con l'utente alla fine del piano
- **Fase:** `in_progress`
- **Ultimo aggiornamento:** 2026-10-29 21:30

## Richieste attive

_Mancanze di progetto che l'agente non può risolvere da solo. L'utente le conferma in chat, poi vengono chiuse con `req-resolve`._

- `R7` (`O19`) Chiave API MiniMax: il proprietario la scrive in ~/.config/agentdeck/minimax.key (permessi 600) sulla Deck

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
  *annotazioni:* `N65`

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

### `O15` Interfacce effimere sullo schermo della Deck: lo stile e la prima interfaccia, le sessioni Claude — BLOCCATO

**Gate obiettivo:** Lo schermo della Deck, al posto del terminale, resta calmo e mostra un'interfaccia grafica effimera solo quando serve; con il tocco o i pulsanti si vedono, si aprono e si chiudono le sessioni Claude; stile deciso come ADR e documentato; versione pubblicata.
**Blocco:** 2026-10-29 20:24 — Approvato dall'utente il 29/10: stile e deck claude fatti; schermo grafico installato, manca la prova al tocco con l'utente alla Deck
**Documenti:** `ADR-0003`

- [x] `O15.T1` Lo stile delle interfacce effimere e la tecnologia grafica dello schermo, decisi con l'utente — *perimetro:* `docs/, PRINCIPI.md`
  *gate previsto:* Regole dello stile e tecnologia grafica (compositore e motore di pagina) confrontate e decise con l'utente, registrate come ADR-0003 e in docs/interfacce.md con l'indice. · *gate confermato:* ✔ Stile (7 regole) e grafica cage+Chromium decisi con l'utente: ADR-0003 accettato, docs/interfacce.md nell'indice, link verificati
  *rischio:* 15/100 — Solo documenti e una decisione; la decisione porta componenti grafici nuovi in T3 (INV-10), quindi va registrata come scelta esplicita dell'utente
  *documenti:* `ADR-0003`
- [x] `O15.T2` La schermata deck claude: elencare, aprire e chiudere le sessioni Claude della Deck — *perimetro:* `deck/, docs/`
  *gate previsto:* deck claude elenca le sessioni con titolo e stato, ne apre una nuova che compare nell'app Claude e ne chiude una con anteprima e conferma, anche come strumenti MCP; test verdi; provato sulla Deck con una sessione di prova senza toccare quelle al lavoro. · *gate confermato:* ✔ deck claude elenca, apre (Remote Control in ~/agentdeck/sessioni) e chiude con conferma; MCP; 259 test; prova sulla Deck, sessioni al lavoro intatte
  *rischio:* 35/100 — Componente nuovo e testato, ma agisce su processi vivi di Claude sulla Deck: chiudere quello sbagliato interrompe il lavoro; close solo su id dall'elenco con conferma, prove solo su sessioni di prova
- [!] `O15.T3` Lo schermo grafico calmo con l'interfaccia effimera delle sessioni, al posto del terminale — *perimetro:* `deck/, docs/, pacchetti grafici e servizio dello schermo sulla Deck`
  *gate previsto:* Sulla Deck lo schermo grafico sostituisce il terminale: di base calmo, l'interfaccia delle sessioni compare con un tocco o un pulsante e sparisce dopo la scelta o il tempo; aprire e chiudere una sessione di prova funziona dal tocco; snapshot prima; ssh agentdeck intatto (INV-1); docs e versione pubblicata. · *blocco:* ✖ Schermo grafico installato (N66, N67); manca la prova al tocco con l'utente alla Deck. Priorità al piano del 29/10
  *rischio:* 55/100 — 112 pacchetti nuovi, utente nuovo, servizio grafico su tty1 e server locale che esegue azioni; snapshot prima, server solo su 127.0.0.1 con codice, ripiego al terminale, ssh verificato a ogni passo
  *documenti:* [piano.md](docs/piano.md)
  *annotazioni:* `N66`, `N67`

### `O16` Lo sviluppo di AgentDeck sta sulla Deck: repository, installazione e revert da qui, versioni fissate (piano punti 10-11) — in corso

**Gate obiettivo:** Il repository vive in /home/agent/agentdeck/repo e si pubblica da qui; un comando deck installa una versione del repository sulla Deck con test, snapshot prima e verifica, e torna alla versione precedente con anteprima; Claude Code a versione fissa senza aggiornamenti automatici; le installazioni senza versione o latest segnalate come errore salvo consenso motivato dell'agente; ssh agentdeck sempre funzionante (INV-1); test; documentazione; versione pubblicata.

_nessuna task. Aggiungile con `wf.sh task-add`._

### `O17` Le richieste di permesso vanno a un arbitro agentico e non bloccano mai l'agente; tabella delle richieste in dashboard (piano punti 8-9) — in corso

**Gate obiettivo:** Le domande della guardia e di Claude Code (hook PermissionRequest) vanno a un arbitro agentico che approva, rifiuta con motivazione o inoltra al proprietario; l'agente non resta mai fermo: via rapida o differita con ritorno della decisione; ogni richiesta in una tabella con stato, sessione e messaggio; deck requests mostra, annulla, sollecita e attende; il numero delle richieste attive in deck status; falsi positivi della guardia ridotti; test; prova reale; documentazione; versione pubblicata.

_nessuna task. Aggiungile con `wf.sh task-add`._

### `O18` Lo sviluppo di AgentDeck sta sulla Deck: repository, installazione e revert da qui, versioni fissate (piano punti 10-11) — chiuso

**Gate obiettivo:** Il repository vive in /home/agent/agentdeck/repo e si pubblica da qui; un comando deck installa una versione del repository sulla Deck con test, snapshot prima e verifica, e torna alla precedente con anteprima; Claude Code a versione fissa senza aggiornamenti automatici; installazioni senza versione o latest segnalate come errore salvo consenso motivato dell'agente; ssh agentdeck sempre funzionante (INV-1); test; documentazione; versione pubblicata.
**Chiuso:** 2026-10-29 20:55 — Approvato dall'utente il 29/10: deck release, Claude Code fisso con prova degli agganci, installazioni a versione fissa; v0.5.5-0.5.7

- [x] `O18.T1` deck installa sulla Deck una versione del repository e torna indietro — *perimetro:* `deck/, docs/, /opt/agentdeck sulla Deck`
  *gate previsto:* Un comando deck installa da /home/agent/agentdeck/repo: test, snapshot prima, copia in /opt/agentdeck, impostazioni Claude (anche bypass nelle impostazioni utente), verifica; revert alla versione precedente con anteprima; provato installando la versione corrente e tornando indietro; ssh intatto; docs/sviluppo.md e deck.md aggiornati. · *gate confermato:* ✔ deck release installa un commit dalla Deck (test, snapshot, scambio atomico, verifica, ritorno automatico) e torna indietro; ciclo reale riuscito, v0.5.5
  *rischio:* 45/100 — Guardia e hook di tutte le sessioni girano da /opt/agentdeck: una versione rotta le bloccherebbe. Snapshot, test prima del cambio, cambio atomico, ritorno automatico se la verifica fallisce.
- [x] `O18.T2` Claude Code a versione fissa, aggiornamento manuale con prova degli agganci — *perimetro:* `deck/, docs/, impostazioni di Claude Code sulla Deck`
  *gate previsto:* Aggiornamenti automatici di Claude Code spenti e versione fissata; un comando o una procedura aggiorna a una versione scelta solo dopo una prova automatica di hook, flag e bypass, con ritorno alla precedente; documentazione. · *gate confermato:* ✔ Aggiornamenti spenti e versione fissata (managed-settings.d); deck claude/version switch con prova degli agganci, provato 2.1.310→2.1.312→2.1.310; v0.5.6
  *rischio:* 35/100 — Tocca il programma di tutte le sessioni: una versione rotta le fermerebbe. Versione precedente conservata, snapshot, prova degli agganci prima del cambio.
- [x] `O18.T3` Installazioni senza versione o latest segnalate come errore, salvo consenso motivato — *perimetro:* `deck/, docs/`
  *gate previsto:* La guardia riconosce le installazioni senza versione o latest fuori da pacman (npm, pip, cargo, curl | sh, immagini :latest, claude) e le rifiuta con il motivo; l'agente le può fare solo dichiarando un consenso motivato, registrato; test con casi veri e falsi positivi; documentazione. · *gate confermato:* ✔ La guardia e deck term rifiutano le installazioni senza versione fuori da pacman, salvo consenso registrato; 57 casi, prova dal vivo; v0.5.7
  *rischio:* 20/100 — Cambia solo cosa la guardia lascia passare; il rischio è bloccare lavoro legittimo, coperto da test sui falsi positivi e dal consenso motivato.
  *annotazioni:* `N68`

### `O19` Le richieste di permesso vanno a un arbitro agentico e non bloccano mai l'agente; tabella delle richieste in dashboard (piano punti 8-9) — in corso

**Gate obiettivo:** Le domande della guardia e di Claude Code (hook PermissionRequest) vanno a un arbitro agentico che approva, rifiuta con motivazione o inoltra al proprietario; l'agente non resta mai fermo (via rapida o differita, decisione che torna); ogni richiesta in una tabella con stato, sessione e messaggio; deck requests mostra, annulla, sollecita e attende; richieste attive in deck status; falsi positivi della guardia ridotti; test; prova reale; documentazione; versione pubblicata.
**Richieste vincolanti:** `R7` Chiave API MiniMax: il proprietario la scrive in ~/.config/agentdeck/minimax.key (permessi 600) sulla Deck

- [x] `O19.T1` Falsi positivi della guardia sui servizi e le credenziali dell'utente — *perimetro:* `deck/agentdeck/ownership.py, deck/claude/, deck/tests/, docs/`
  *gate previsto:* Le catene di sola lettura (cd, test, systemctl cat o status di agentdeck-servizio@) non chiedono più; gli interventi veri sì; test con i casi osservati il 29/10; documentazione. · *gate confermato:* ✔ Mai più domande all'utente (deny al posto di ask, root consentita, hook PermissionRequest); heredoc e letture non più falsi positivi; v0.5.8
  *rischio:* 25/100 — Allargare troppo farebbe passare senza domanda un intervento vero su un servizio o una credenziale del proprietario; test su entrambi i lati.
- [!] `O19.T2` Tabella delle richieste e deck requests, con il numero in deck status — *perimetro:* `deck/, docs/`
  *gate previsto:* SQLite di sistema con id, stato, sessione, messaggio, comando, motivo, decisore, decisione, scadenza, solleciti; deck requests elenca, mostra, annulla, sollecita e attende con timeout, anche via MCP; avviso in deck status con le richieste attive; test; documentazione. · *blocco:* ✖ Non sviluppata dall'agente in questa sessione: da rivedere con l'utente alla fine del piano
  *rischio:* 25/100 — Componente nuovo e testato; la guardia in più scrive le richieste in un database: un errore lì non deve mai bloccare un comando.
  *documenti:* [piano.md](docs/piano.md)
- [ ] `O19.T3` L'arbitro agentico decide al posto dell'umano senza bloccare l'agente — *perimetro:* `deck/, docs/, servizi e impostazioni di Claude Code sulla Deck`
  *gate previsto:* La guardia e l'hook PermissionRequest mandano le richieste all'arbitro (istanza senza memorie, prompt del sistema, trascrizione come dato); via rapida di pochi secondi, poi differita con deny e ritorno della decisione, approvazione monouso legata al comando; inoltro al proprietario segnato in attesa finché non c'è Telegram; test; prova reale; documentazione.
  *annotazioni:* `N69`

### `O20` L'agente interno di AgentDeck: MiniMax via Claude Code con un intermediario locale, identità AgentDeck (piano punto 1) — in corso

**Gate obiettivo:** Un intermediario locale passa le richieste di Claude Code a MiniMax togliendo la riga fissa Claude e i parametri non supportati; prompt di sistema con l'identità AgentDeck di HoneyLabs; deck agent lancia l'agente su un compito con strumenti deck e guardia attiva; attivazione per eventi e a intervalli con autonomia a livelli (le azioni rischiose solo segnalate); registro delle attività; prova con un finto MiniMax e prova reale con la chiave; documentazione; versione pubblicata.

- [~] `O20.T1` Intermediario locale verso MiniMax: toglie la riga fissa Claude e adatta la richiesta — *perimetro:* `deck/, docs/, servizio dell'intermediario sulla Deck`
  *gate previsto:* Servizio su 127.0.0.1 che riceve le richieste di Claude Code, toglie la riga fissa e l'intestazione di fatturazione, adatta modello, parametri e intestazioni, inoltra a MiniMax con la chiave letta dalla Deck e restituisce lo streaming; provato con un finto MiniMax e con claude -p; chiave mai nel repository; documentazione.
  *rischio:* 20/100 — Servizio solo locale su 127.0.0.1; la chiave sta solo sulla Deck; nessun cambiamento alle sessioni esistenti.
- [ ] `O20.T2` Prompt di sistema AgentDeck e deck agent per lanciare l'agente su un compito — *perimetro:* `deck/, docs/`
  *gate previsto:* Prompt di sistema generato dal sistema con l'identità AgentDeck di HoneyLabs, regole e invarianti; deck agent run lancia claude -p con quel prompt, strumenti deck, guardia e intermediario, e registra esito e attività; provato con il finto MiniMax e, con la chiave, con un compito di sola lettura; documentazione.
- [ ] `O20.T3` Attivazione per eventi e a intervalli, autonomia a livelli — *perimetro:* `deck/, docs/, timer e servizi sulla Deck`
  *gate previsto:* Timer e avvisi critici attivano l'agente interno; può fare da solo solo diagnosi e azioni a basso rischio, le altre le segnala; registro consultabile da deck agent; provato con un avviso simulato; documentazione.

## Annotazioni

_Una riga per nota, sempre legata a una task. `wf.sh notes` per leggerle._

- `N58` (`O12.T1`) Precisazione dell'utente (26/10) su ADR-0001, cosa sono i dati dell'utente: i suoi servizi in /srv/servizi/<nome> (codice, configurazione, dati, segreti, avvio, arresto, abilitazione delle unità agentdeck-servizio@<nome>) e le sue credenziali (login di Claude, chiavi SSH). Sui progetti che l'utente chiede all'agente, come /home/agent/frugale, l'agente lavora libero. Vincolo di questo momento: una sessione di Remote Control sta lavorando a frugale; l'installazione sulla Deck riavvia agentdeck-claude e la chiuderebbe, quindi si installa solo quando l'utente dice che la sessione è finita. — 2026-10-26 17:56
- `N59` (`O12.T1`) Stato (26/10 18:00): politica pronta e provata sul Mac (agentdeck/ownership.py, guardia con permissionDecision ask, allow di tutto il lavoro di sistema nelle impostazioni gestite, testi senza richieste al proprietario per il sistema, 241 test). Non installata: sulla Deck è attiva la sessione di Remote Control su frugale (ultima attività 17:57) e deck/claude/install.sh riavvia agentdeck-claude. Restano installazione e prova con claude -p senza permessi aggiuntivi. — 2026-10-26 17:59
- `N60` (`O14.T1`) Caso reale (26/10, su richiesta dell'utente, fuori dal perimetro di O12.T1): pubblicato il progetto frugale nato sulla Deck, come chiede la sua decisione 0009. Repository privato panicDa3m0n/frugale; clone sul Mac in /Users/snj/frugale con remote deck (agentdeck:/home/agent/frugale) e origin HTTPS con credential helper locale di panicDa3m0n (come P1); push di main (de60013, bbe2177). Il ponte è manuale: per ogni aggiornamento serve git pull deck main e git push origin main dal Mac. È il bisogno N52 anche per i progetti dell'utente, non solo per AgentDeck. — 2026-10-26 18:20
- `N61` (`O14.T2`) Adattatore: nei menu a frecce (gh auth login) le opzioni sotto la riga del cursore non entrano in question.options; servirebbe una regola o un profilo per i menu a frecce (segnalato dall'agente della Deck il 26/10, scritto in docs/adattatore.md, Limiti noti) — 2026-10-26 18:53
- `N62` (`O14.T2`) Stato O14.T2 (26/10 18:56): nel repository pronti ownership con il login GitHub come credenziale, correzione Go dell'adattatore (P23), regola GitHub in CLAUDE.template.md, docs; risposta all'agente della Deck data all'utente. Manca la prova del gate: il push di frugale dalla Deck (origin ancora assente, 3 commit non pubblicati). Copia doppia /Users/snj/frugale/frugale spostata nel Cestino su richiesta dell'utente. — 2026-10-26 18:57
- `N63` (`O12.T1`) Sulla Deck (27/10): SendMessage aggiunto a permissions.allow di /etc/claude-code/managed-settings.json (copia .bak-sendmessage), su richiesta dell'utente: l'agente non deve aspettare un clic per scrivere a un'altra chat. Sulla Deck è installato ancora solo mcp__deck: tutta la politica ADR-0001 resta da installare; stessa voce nel repository e in docs/claude-code.md. Copiato anche il token Baxi nei segreti di domus (600, srv-domus), su richiesta dell'utente. — 2026-10-27 18:44
- `N64` (`O13.T1`) Servizio domus (27/10, su richiesta dell'utente dalla sessione della Deck): token Baxi copiato in /srv/servizi/domus/dati/secrets (600, srv-domus), /state funziona sulla Deck; motore Domus sul Mac (PID 35282, *:8777, avviato a mano, non da launchd) fermato con SIGINT, porta 8777 chiusa; resta sul Mac un'istanza di prova su 127.0.0.1:8778 (PID 46342), non toccata. — 2026-10-27 19:47
- `N65` (`O12.T5`) Obblighi troppo larghi: l'installazione di cage + chromium (O15.T3) ha aperto 47 PROFILE_NEEDED, uno per ogni pacchetto con programmi, librerie trascinate comprese (avahi, gtk, spirv...); chiusi tutti con dismiss e motivo. L'hook dovrebbe considerare solo i pacchetti installati esplicitamente (pacman -Qe) o i programmi davvero interattivi. — 2026-10-27 23:12
- `N66` (`O15.T3`) Sulla Deck (28/10, sessione gestione-deck, decisione dell'utente): tutte le sessioni Claude Code in bypassPermissions (managed-settings senza disableBypassPermissionsMode, defaultMode e skipDangerousModePermissionPrompt) e ogni sessione aperta da deck claude è un servizio suo, agentdeck-sessione@<nome>. Fatto direttamente in /opt/agentdeck; portato nel repository il 29/10 dalla Deck, con docs/claude-code.md e docs/interfacce.md; 270 test verdi sulla Deck. — 2026-10-29 20:18
- `N67` (`O15.T3`) Piano del 29/10 deciso con l'utente (docs/piano.md): sviluppo di AgentDeck sulla Deck con installazione e revert da qui, versioni fissate (Claude Code, niente installazioni latest senza consenso), arbitro agentico al posto delle domande della guardia senza mai bloccare l'agente, tabella delle richieste in dashboard, agente interno MiniMax con intermediario, Telegram, Brain. Da tradurre in obiettivi con un nuovo ciclo. O15.T3 resta aperta (prova al tocco). — 2026-10-29 20:18
- `N68` (`O18.T3`) Falso positivo di claude/after.py (29/10): un comando che conteneva solo testo 'pacman -S' fra virgolette (casi di prova di O18.T3) ha fatto dire all'hook che erano stati installati pacchetti; non è stato installato nulla. Andrebbe controllato se pacman è davvero partito (log o database) invece del testo del comando. — 2026-10-29 20:52
- `N69` (`O19.T3`) Da rivedere con l'utente alla fine del piano, insieme a O19.T2: non sviluppata dall'agente in questa sessione (29/10). Già fatto in O19.T1: nessuna domanda all'utente, deny con motivo, hook PermissionRequest che registra. — 2026-10-29 21:29
