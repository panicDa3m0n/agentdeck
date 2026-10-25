<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 03: Studio dell'architettura agent-first: come funziona il sistema e dove intercettarlo

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** `O8` Mappa del sistema e architettura agent-first — 7 task: 6 completate, 1 in corso, 0 da fare, 0 bloccate
- **Task attiva:** `O8.T7` Sintesi: architettura proposta e decisioni — in corso · rischio 5/100
- **Ultima task gestita:** `O8.T6` — completata — Sezione 6 di architettura.md: fork di Claude Code non permesso (licenza), Agent SDK, hook, MCP, Remote Control verificati; dove vivono le sessioni; 6 proposte
- **Fase:** `in_progress`
- **Ultimo aggiornamento:** 2026-10-25 23:27

## Richieste attive

_Mancanze di progetto che l'agente non può risolvere da solo. L'utente le conferma in chat, poi vengono chiuse con `req-resolve`._

- `R3` (generale) Confermare il ciclo 03: eseguire dal terminale dell'utente i 15 debt-resolve approvati il 25/10, negati all'agente nel passo 6 del setup (P10)

## Obiettivi

### `O8` Mappa del sistema e architettura agent-first — in corso

**Gate obiettivo:** docs/architettura.md approvato dall'utente: per ogni strato come funziona (misurato sulla Deck), i presupposti umani, i punti in cui il sistema si può intercettare e la proposta per livello (INV-10); decisioni di architettura approvate una per una; nessuna modifica alla Deck durante lo studio.

- [x] `O8.T1` Avvio, kernel e ripristino — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione avvio: firmware, GRUB, initramfs, avvio di systemd misurati sulla Deck (systemd-analyze, journal, configurazioni); dove serve un umano (console, password di root in emergenza, menu); come ripartire da soli da uno stato buono; limite GRUB ed EFI (N17); proposte per livello. · *gate confermato:* ✔ Sezione 1 di architettura.md: avvio misurato (20 s), 8 presupposti umani (root bloccato in emergenza, panic, watchdog spento), 11 proposte
  *rischio:* 5/100 — Solo letture sulla Deck (configurazioni, journal, systemd-analyze) e scrittura di docs/architettura.md: nessuna modifica al sistema.
- [x] `O8.T2` Init, servizi e interfacce del sistema — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione interfacce: systemd, D-Bus, varlink, socket, /proc e /sys contro i comandi testuali per umani; quali parti offrono già API strutturate e quali no; come deck può parlare al sistema senza passare dal testo; proposte per livello. · *gate confermato:* ✔ Sezione 2 di architettura.md: 18 socket varlink e D-Bus misurati (8 ms), deck usa 12 parser di testo; 6 presupposti umani, 7 proposte
  *rischio:* 5/100 — Solo letture sulla Deck (bus di sistema, socket varlink, uscite dei comandi) e scrittura di docs/architettura.md: nessuna modifica al sistema.
- [x] `O8.T3` Identità, permessi, isolamento e segreti dell'agente — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione identità: utenti, PAM, sudo, polkit, capabilities, sandbox di systemd, Landlock; segreti con systemd-creds e TPM della Deck (N14); dall'agente con sudo totale a permessi mirati e tracciati; proposte per livello. · *gate confermato:* ✔ Sezione 3 di architettura.md: sudo ALL senza polkit, nessuna sandbox né audit né firewall, TPM e Landlock pronti; 6 presupposti umani, 8 proposte
  *rischio:* 5/100 — Solo letture sulla Deck (utenti, PAM, sudo, polkit, sandbox, TPM, credenziali) e scrittura di docs/architettura.md: nessuna modifica al sistema.
- [x] `O8.T4` Stato del sistema, software e snapshot — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione stato: subvolumi, pacman e i suoi hook, configurazione imperativa contro stato desiderato con differenze e rollback, isolamento dei carichi, politica degli snapshot e pulizia (N15, N20, O7.T2); proposte per livello. · *gate confermato:* ✔ Sezione 4 di architettura.md: 32 snapshot (19 senza pulizia), configurazione imperativa in 24 file, sysext e nspawn pronti; 5 presupposti umani, 8 proposte
  *rischio:* 5/100 — Solo letture sulla Deck (subvolumi, snapper, pacman, /etc, estensioni di systemd) e scrittura di docs/architettura.md: nessuna modifica al sistema.
- [x] `O8.T5` Eventi, log e osservabilità — *perimetro:* `docs/architettura.md, letture sulla Deck`
  *gate previsto:* Sezione eventi: journal, udev, eventi di systemd e D-Bus, inotify, audit, timer; cosa può svegliare un agente e come diventa autoprompting (contesto e istruzioni al momento giusto); proposte per livello. · *gate confermato:* ✔ Sezione 5 di architettura.md: journal (28% traccia agente, 42% eventi riconoscibili), sistema silenzioso, nessuno sveglia l'agente; 5 presupposti, 9 proposte
  *rischio:* 5/100 — Solo letture e osservazioni di pochi secondi sulla Deck (journal, D-Bus, udev, timer, logind) e scrittura di docs/architettura.md: nessuna modifica al sistema.
- [x] `O8.T6` L'harness dell'agente: Claude Code e alternative — *perimetro:* `docs/architettura.md`
  *gate previsto:* Sezione harness: licenza di Claude Code e possibilità di fork verificate su fonti ufficiali; Claude Agent SDK; estensione senza fork (hook, MCP, plugin, skill, modalità senza interfaccia, Remote Control); dove vivono le sessioni e come il sistema alimenta comandi interattivi e autoprompting; proposta motivata. · *gate confermato:* ✔ Sezione 6 di architettura.md: fork di Claude Code non permesso (licenza), Agent SDK, hook, MCP, Remote Control verificati; dove vivono le sessioni; 6 proposte
  *rischio:* 5/100 — Ricerca su fonti ufficiali e letture sulla Deck; scrittura di docs/architettura.md: nessuna modifica al sistema.
- [~] `O8.T7` Sintesi: architettura proposta e decisioni — *perimetro:* `docs/architettura.md, PRINCIPI.md`
  *gate previsto:* Architettura complessiva in una pagina, con le interfacce per l'umano come canale futuro ed effimero; elenco delle decisioni approvate una per una dall'utente; roadmap degli sviluppi che ne deriva, pronta per il ciclo successivo.
  *rischio:* 5/100 — Sintesi scritta in docs/architettura.md e PRINCIPI.md, nessuna modifica alla Deck; le decisioni le prende l'utente in revisione.
  *annotazioni:* `N21`, `N22`, `N23`

### `O9` Aggiornamento reale della Deck con deck update — in corso

**Gate obiettivo:** Il primo aggiornamento vero di Arch applicato con deck update: anteprima, snapshot prima e dopo, verifica, riavvio se richiesto; la Deck resta raggiungibile (INV-1).

- [ ] `O9.T1` Prova di deck update con un aggiornamento vero (ripresa di O6.T1, con N16, N18, N19) — *perimetro:* `deck/, componente update, pacchetti sulla Deck`
  *gate previsto:* deck update elenca l'aggiornamento con versioni e segnala kernel e GRUB; apply con conferma crea gli snapshot, aggiorna, verifica servizi e accesso; riavvio e verify se richiesti; ssh agentdeck funziona dopo.

## Annotazioni

_Una riga per nota, sempre legata a una task. `wf.sh notes` per leggerle._

- `N21` (`O8.T7`) Da portare alla revisione (O8.T6, 25/10): la licenza di Claude Code (LICENSE.md: All rights reserved, termini commerciali di Anthropic) non permette un fork. Proposta A6.1: Claude Code non modificato più un plugin di AgentDeck (hook, MCP con deck mcp, skill, CLAUDE.md), Agent SDK per gli agenti nostri, Remote Control per seguire le sessioni dal telefono. Cambia l'idea iniziale dell'utente: va decisa esplicitamente. — 2026-10-25 23:22
- `N22` (`O8.T7`) Decisione dell'utente (25/10, D1): niente API di Claude, l'harness è Claude Code. Sessioni interattive: Claude Code sulla Deck con il plugin di AgentDeck (hook, deck mcp, skill), seguite con Remote Control. Agente autonomo: Claude Code senza interfaccia (claude -p, --resume), non Agent SDK con chiave API; fork open source escluso. Da verificare: condizioni d'uso dell'abbonamento per sessioni automatiche; testo di INV-7 (modelli via API cloud) da allineare con il sì dell'utente. — 2026-10-25 23:25
- `N23` (`O8.T7`) Verifica dei termini (25/10, fonti primarie): Consumer Terms vietano reverse engineering e accesso automatizzato salvo chiave API o permesso esplicito; il login dell'abbonamento è per l'uso ordinario di Claude Code; il binario non va modificato. Sessioni interattive e Remote Control in regola; sessioni avviate da eventi con claude -p sull'abbonamento da chiarire prima di A5.5/A6.5 (decisione D7). — 2026-10-25 23:27
