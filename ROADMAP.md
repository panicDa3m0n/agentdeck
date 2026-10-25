<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 03: Studio dell'architettura agent-first: come funziona il sistema e dove intercettarlo

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** —
- **Task attiva:** —
- **Ultima task gestita:** —
- **Ultimo aggiornamento:** 2026-10-25 20:44

## Richieste attive

_Mancanze di progetto che l'agente non può risolvere da solo. L'utente le conferma in chat, poi vengono chiuse con `req-resolve`._

- `R3` (generale) Confermare il ciclo 03: eseguire dal terminale dell'utente i 15 debt-resolve approvati il 25/10, negati all'agente nel passo 6 del setup (P10)

## Obiettivi

### `O8` Mappa del sistema e architettura agent-first — in corso

**Gate obiettivo:** docs/architettura.md approvato dall'utente: per ogni strato come funziona (misurato sulla Deck), i presupposti umani, i punti in cui il sistema si può intercettare e la proposta per livello (INV-10); decisioni di architettura approvate una per una; nessuna modifica alla Deck durante lo studio.

- [ ] `O8.T1` Avvio, kernel e ripristino — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione avvio: firmware, GRUB, initramfs, avvio di systemd misurati sulla Deck (systemd-analyze, journal, configurazioni); dove serve un umano (console, password di root in emergenza, menu); come ripartire da soli da uno stato buono; limite GRUB ed EFI (N17); proposte per livello.
- [ ] `O8.T2` Init, servizi e interfacce del sistema — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione interfacce: systemd, D-Bus, varlink, socket, /proc e /sys contro i comandi testuali per umani; quali parti offrono già API strutturate e quali no; come deck può parlare al sistema senza passare dal testo; proposte per livello.
- [ ] `O8.T3` Identità, permessi, isolamento e segreti dell'agente — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione identità: utenti, PAM, sudo, polkit, capabilities, sandbox di systemd, Landlock; segreti con systemd-creds e TPM della Deck (N14); dall'agente con sudo totale a permessi mirati e tracciati; proposte per livello.
- [ ] `O8.T4` Stato del sistema, software e snapshot — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione stato: subvolumi, pacman e i suoi hook, configurazione imperativa contro stato desiderato con differenze e rollback, isolamento dei carichi, politica degli snapshot e pulizia (N15, N20, O7.T2); proposte per livello.
- [ ] `O8.T5` Eventi, log e osservabilità — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione eventi: journal, udev, eventi di systemd e D-Bus, inotify, audit, timer; cosa può svegliare un agente e come diventa autoprompting (contesto e istruzioni al momento giusto); proposte per livello.
- [ ] `O8.T6` L'harness dell'agente: Claude Code e alternative — *perimetro:* `docs/architettura.md`
  *gate previsto:* Sezione harness: licenza di Claude Code e possibilità di fork verificate su fonti ufficiali; Claude Agent SDK; estensione senza fork (hook, MCP, plugin, skill, modalità senza interfaccia, Remote Control); dove vivono le sessioni e come il sistema alimenta comandi interattivi e autoprompting; proposta motivata.
- [ ] `O8.T7` Sintesi: architettura proposta e decisioni — *perimetro:* `docs/architettura.md, PRINCIPI.md`
  *gate previsto:* Architettura complessiva in una pagina, con le interfacce per l'umano come canale futuro ed effimero; elenco delle decisioni approvate una per una dall'utente; roadmap degli sviluppi che ne deriva, pronta per il ciclo successivo.

### `O9` Aggiornamento reale della Deck con deck update — in corso

**Gate obiettivo:** Il primo aggiornamento vero di Arch applicato con deck update: anteprima, snapshot prima e dopo, verifica, riavvio se richiesto; la Deck resta raggiungibile (INV-1).

- [ ] `O9.T1` Prova di deck update con un aggiornamento vero (ripresa di O6.T1, con N16, N18, N19) — *perimetro:* `deck/, componente update, pacchetti sulla Deck`
  *gate previsto:* deck update elenca l'aggiornamento con versioni e segnala kernel e GRUB; apply con conferma crea gli snapshot, aggiorna, verifica servizi e accesso; riavvio e verify se richiesti; ssh agentdeck funziona dopo.

## Annotazioni

_nessuna annotazione._
