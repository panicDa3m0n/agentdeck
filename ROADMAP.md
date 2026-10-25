<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 04: Claude Code dentro AgentDeck: installazione, configurazione e uso reale

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** `O10` Claude Code sulla Deck, usato davvero — 4 task: 1 completate, 0 in corso, 2 da fare, 1 bloccate
- **Task attiva:** —
- **Ultima task gestita:** `O10.T2` — bloccata — Rinviata dall'utente: manca il login di Claude Code con l'abbonamento (R4). Pronti tmux e ~/agentdeck; si riprende dal login nel Terminale
- **Ultimo aggiornamento:** 2026-10-26 00:03

## Richieste attive

_Mancanze di progetto che l'agente non può risolvere da solo. L'utente le conferma in chat, poi vengono chiuse con `req-resolve`._

- `R4` (`O10`) Login di Claude Code sulla Deck con l'abbonamento: l'utente autorizza dal browser e incolla il codice nella scheda del terminale aperta per il login

## Obiettivi

### `O10` Claude Code sulla Deck, usato davvero — in corso

**Gate obiettivo:** Claude Code gira sulla Deck per l'utente agent, autenticato con l'abbonamento e seguibile con Remote Control; conosce AgentDeck da un CLAUDE.md ricavato da docs/ e usa deck; una sessione di lavoro reale dalla chat produce i bisogni per il ciclo successivo; snapshot prima di ogni modifica e ssh agentdeck sempre funzionante (INV-1).
**Richieste vincolanti:** `R4` Login di Claude Code sulla Deck con l'abbonamento: l'utente autorizza dal browser e incolla il codice nella scheda del terminale aperta per il login

- [x] `O10.T1` Installazione di Claude Code sulla Deck — *perimetro:* `pacchetti e file dell'utente agent sulla Deck, install/, deck/, docs/`
  *gate previsto:* Snapshot prima; binario nativo di Claude Code installato per l'utente agent con firma GPG del manifest e checksum verificate; claude --version e claude doctor funzionano su Arch (la prima richiesta vera passa a O10.T2, dopo il login: decisione dell'utente); nessun servizio esposto in rete; installazione ripetibile da script del repository; documentazione aggiornata. · *gate confermato:* ✔ Claude Code 2.1.310 sulla Deck per agent: firma GPG del manifest e checksum verificate, --version e doctor ok, nessuna porta nuova; install/claude-code.sh
  *rischio:* 25/100 — Installa sulla Deck un programma che esegue comandi; qui non viene ancora usato come agente, non tocca rete né servizi, snapshot prima, nessun servizio esposto.
- [!] `O10.T2` Accesso: abbonamento, sessione persistente e Remote Control (N22, N23) — *perimetro:* `configurazione di Claude Code e unità systemd sulla Deck, docs/, pacchetto tmux sulla Deck`
  *gate previsto:* Login con l'abbonamento fatto dall'utente, token solo sulla Deck (INV-6); prima richiesta di prova riuscita; sessione di Claude Code come servizio che sopravvive alla caduta di SSH; raggiungibile con Remote Control da claude.ai o dal telefono; termini dell'abbonamento per sessioni automatiche verificati e riportati; proposta di nuovo testo per INV-7. · *blocco:* ✖ Rinviata dall'utente: manca il login di Claude Code con l'abbonamento (R4). Pronti tmux e ~/agentdeck; si riprende dal login nel Terminale
  *rischio:* 30/100 — Collega l'account dell'utente e lascia un agente in esecuzione sulla Deck: snapshot prima, nessuna porta in ascolto (Remote Control lavora in uscita), token solo sulla Deck e login fatto dall'utente.
  *annotazioni:* `N27`, `N28`
- [ ] `O10.T3` Prima configurazione: AgentDeck spiegato a Claude Code — *perimetro:* `CLAUDE.md e impostazioni di Claude Code sulla Deck, deck/, docs/`
  *gate previsto:* CLAUDE.md di AgentDeck ricavato da docs/ (fonte unica, INV-9) con principi, invarianti e uso di deck; permessi di Claude Code che proteggono l'accesso (niente stop o disable di sshd, rete, iwd, dbus); uso di deck dalla sessione verificato.
- [ ] `O10.T4` Uso reale dalla chat e bisogni emersi — *perimetro:* `sessioni di Claude Code sulla Deck, annotazioni della governance, docs/`
  *gate previsto:* Almeno una sessione di lavoro reale dalla chat di Claude Code sulla Deck, scelta con l'utente; ogni bisogno emerso registrato come annotazione; proposta di roadmap del ciclo successivo che nasce da quei bisogni.

### `O11` Aggiornamento reale della Deck con deck update (O9) — in corso

**Gate obiettivo:** Il primo aggiornamento vero di Arch applicato con deck update: anteprima, snapshot prima e dopo, verifica, riavvio se richiesto; la Deck resta raggiungibile (INV-1).

- [ ] `O11.T1` Prova di deck update con un aggiornamento vero (O9.T1, N26; da O6.T1, O6, N16, N18, N19) — *perimetro:* `deck/, componente update, pacchetti sulla Deck`
  *gate previsto:* deck update elenca l'aggiornamento con versioni e segnala kernel e GRUB; apply con conferma crea gli snapshot, aggiorna, verifica servizi e accesso; riavvio e verify se richiesti; ssh agentdeck funziona dopo.

## Annotazioni

_Una riga per nota, sempre legata a una task. `wf.sh notes` per leggerle._

- `N27` (`O10.T2`) Da O10.T1 (25/10): le sessioni SSH non interattive di agent non leggono ~/.bashrc, quindi claude non è nel PATH dei comandi lanciati via ssh (PATH di sshd: /usr/local/sbin:/usr/local/bin:/usr/bin). Per il servizio di Claude Code impostare PATH nell'unità systemd; per i comandi via ssh usare ~/.local/bin/claude o decidere un collegamento di sistema (fuori dal perimetro di O10.T1). — 2026-10-25 23:55
- `N28` (`O10.T2`) Effetto del rinvio del login (26/10, decisione dell'utente): senza login con l'abbonamento (R4) non si fanno richiesta di prova, Remote Control né il servizio persistente; restano pronti tmux 3.8 (snapshot 36-38) e la cartella di lavoro ~/agentdeck. O10.T3 si può preparare (CLAUDE.md, permessi) ma la verifica dalla sessione richiede il login; O10.T4 richiede il login. tmux va aggiunto all'elenco pacchetti di install/install.sh. Per il login usare una scheda del Terminale (P18). — 2026-10-26 00:03
