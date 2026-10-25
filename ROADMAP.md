<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 04: Claude Code dentro AgentDeck: installazione, configurazione e uso reale

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** —
- **Task attiva:** —
- **Ultima task gestita:** —
- **Ultimo aggiornamento:** 2026-10-25 23:50

## Richieste attive

_nessuna richiesta in attesa._

## Obiettivi

### `O10` Claude Code sulla Deck, usato davvero — in corso

**Gate obiettivo:** Claude Code gira sulla Deck per l'utente agent, autenticato con l'abbonamento e seguibile con Remote Control; conosce AgentDeck da un CLAUDE.md ricavato da docs/ e usa deck; una sessione di lavoro reale dalla chat produce i bisogni per il ciclo successivo; snapshot prima di ogni modifica e ssh agentdeck sempre funzionante (INV-1).

- [ ] `O10.T1` Installazione di Claude Code sulla Deck — *perimetro:* `pacchetti e file dell'utente agent sulla Deck, install/, deck/, docs/`
  *gate previsto:* Snapshot prima; binario nativo di Claude Code installato per l'utente agent; claude --version e una richiesta di prova funzionano su Arch; nessun servizio esposto in rete; installazione ripetibile da script del repository; documentazione aggiornata.
- [ ] `O10.T2` Accesso: abbonamento, sessione persistente e Remote Control (N22, N23) — *perimetro:* `configurazione di Claude Code e unità systemd sulla Deck, docs/`
  *gate previsto:* Login con l'abbonamento fatto dall'utente, token solo sulla Deck (INV-6); sessione di Claude Code come servizio che sopravvive alla caduta di SSH; raggiungibile con Remote Control da claude.ai o dal telefono; termini dell'abbonamento per sessioni automatiche verificati e riportati; proposta di nuovo testo per INV-7.
- [ ] `O10.T3` Prima configurazione: AgentDeck spiegato a Claude Code — *perimetro:* `CLAUDE.md e impostazioni di Claude Code sulla Deck, deck/, docs/`
  *gate previsto:* CLAUDE.md di AgentDeck ricavato da docs/ (fonte unica, INV-9) con principi, invarianti e uso di deck; permessi di Claude Code che proteggono l'accesso (niente stop o disable di sshd, rete, iwd, dbus); uso di deck dalla sessione verificato.
- [ ] `O10.T4` Uso reale dalla chat e bisogni emersi — *perimetro:* `sessioni di Claude Code sulla Deck, annotazioni della governance, docs/`
  *gate previsto:* Almeno una sessione di lavoro reale dalla chat di Claude Code sulla Deck, scelta con l'utente; ogni bisogno emerso registrato come annotazione; proposta di roadmap del ciclo successivo che nasce da quei bisogni.

### `O11` Aggiornamento reale della Deck con deck update (O9) — in corso

**Gate obiettivo:** Il primo aggiornamento vero di Arch applicato con deck update: anteprima, snapshot prima e dopo, verifica, riavvio se richiesto; la Deck resta raggiungibile (INV-1).

- [ ] `O11.T1` Prova di deck update con un aggiornamento vero (O9.T1, N26; da O6.T1, O6, N16, N18, N19) — *perimetro:* `deck/, componente update, pacchetti sulla Deck`
  *gate previsto:* deck update elenca l'aggiornamento con versioni e segnala kernel e GRUB; apply con conferma crea gli snapshot, aggiorna, verifica servizi e accesso; riavvio e verify se richiesti; ssh agentdeck funziona dopo.

## Annotazioni

_nessuna annotazione._
