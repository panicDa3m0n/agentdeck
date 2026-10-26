# Changelog

Storia delle versioni di AgentDeck. Schema MAJOR.MINOR.PATCH gestito dalla governance: il terzo numero
sale a ogni task completata, il secondo a ogni ciclo chiuso, il primo solo con il sì dell'utente.
Ogni versione è pubblicata su https://github.com/panicDa3m0n/agentdeck con il tag `v<versione>`.

## 0.4.8 — 2026-10-26

Ciclo 04, task O10.T10, ripresa di O10.T5: l'accesso alla Deck da fuori casa è verificato
([docs/accesso.md](docs/accesso.md)).

- La regola sul router (TCP 49222 verso 192.168.1.49:22) è attiva.
- Dall'hotspot del telefono:
  - `ssh agentdeck` ha scelto da solo `scarlethome.ddns.net:49222` ed è entrato in 3 secondi;
  - la Deck vede l'indirizzo esterno vero, quindi sshguard può bloccare chi sbaglia;
  - `deck status` risponde, e `deck/install.sh` completo dura 35 secondi.
- Da casa il router rigira le connessioni via nome pubblico con il proprio IP ("hairpin"). `ssh agentdeck` in casa
  usa la LAN.
- Nuovo `install/remote-check.sh`, per ripetere la prova: porta il Mac sull'hotspot (la password la scrive
  l'utente e non viene salvata), verifica, e lo riporta sul Wi-Fi di casa.
- Osservato: dopo il riavvio del router la Deck è sul Wi-Fi a 2,4 GHz (`WIFI_BAND_2G`).

## 0.4.7 — 2026-10-26

Ciclo 04, task O10.T9: le skill di AgentDeck per Claude Code e la prova d'insieme
([docs/claude-code.md](docs/claude-code.md)).

- **Sei skill**, le procedure del sistema:
  - installare un pacchetto, cambiare un servizio;
  - usare un programma interattivo, con la guida ai profili;
  - gestire avvisi e obblighi;
  - tornare indietro, aggiornare il sistema.

  Le copia `deck/claude/install.sh` in `~/.claude/skills/agentdeck-*` sulla Deck, senza toccare le altre skill.
- **Test:** ogni strumento MCP citato dalle skill esiste davvero fra quelli di `deck mcp`.
- **Prova d'insieme:** a "Installa il programma tree sulla Deck e dimmi se funziona", una sessione sulla Deck:
  - ha caricato da sola la skill di installazione;
  - ha installato con l'adattatore e chiuso con una nota l'obbligo aperto dall'hook di pacman;
  - ha verificato e riferito.

  Poi `tree` è stato rimosso.
- `claude-code.md` ha la pagina d'insieme di AgentDeck per Claude Code.
- Annotato per O10.T4 (N46) il bisogno emerso: una politica di permessi per i comandi Bash di sola lettura.
- 229 test.

## 0.4.6 — 2026-10-26

Ciclo 04, task O10.T8: gli obblighi del sistema e gli hook di autoprompting per Claude Code
([docs/obblighi.md](docs/obblighi.md), [docs/claude-code.md](docs/claude-code.md)).

- **`deck obligations`:** i doveri che il sistema dà all'agente, per ora solo avvisi, con `show`, `done` con una
  nota, `dismiss` con il motivo e `installed`. Il primo è `PROFILE_NEEDED`: dopo un'installazione, il profilo
  dell'adattatore per i programmi nuovi.
- **L'obbligo nasce dal sistema:**
  - un hook di pacman (`/etc/pacman.d/hooks/95-agentdeck-obligations.hook`), con lo script di root in
    `/usr/local/lib/agentdeck/`, scatta a ogni installazione, chiunque la faccia;
  - l'obbligo si chiude da sé quando tutti i profili esistono o il pacchetto è rimosso.
- **Protocollo:** il campo facoltativo `obligations` (sezione 6 bis) porta gli obblighi aperti in ogni schermata e
  quindi in ogni risultato MCP. I messaggi sono testo del sistema.
- **Hook di Claude Code:**
  - `SessionStart` riporta anche obblighi e sessione precedente;
  - `UserPromptSubmit` porta solo le novità del turno;
  - `PreToolUse` indica l'azione di `deck` al posto del comando grezzo, senza bloccare;
  - `PostToolUse` dà le verifiche dopo Bash e le modifiche ai file, più gli obblighi nuovi;
  - `SessionEnd` scrive il registro delle sessioni.
- **Provato da sessioni vere sulla Deck:**
  - installazione di `cowsay`, obbligo ricevuto, verificato e chiuso dall'agente;
  - obbligo nato in un turno e arrivato all'inizio del successivo;
  - suggerimento prima di `journalctl`;
  - registro con 14 chiamate di strumenti.
- 225 test.

## 0.4.5 — 2026-10-26

Ciclo 04, task O10.T7: l'adattatore dei programmi interattivi, `deck term` ([docs/adattatore.md](docs/adattatore.md)).

- **Un terminale che vede solo l'agente.** Un programma gira in tmux, su un server tutto suo, e torna come
  schermata:
  - `session`: stato `running`, `waiting_input`, `stalled` o `exited`;
  - `terminal`: righe, righe nuove, cursore, eco;
  - `question`: tipo, opzioni, predefinito, origine;
  - `parsed`.
- **Azioni:** `start`, `show`, `answer`, `choose`, `key`, `wait`, `interrupt`, `close` con conferma, e
  `profile_save`, `profile_show`, `profile_test`. Da Claude Code sono gli strumenti `mcp__deck__term_*`.
- **Riconoscimento:** il profilo del programma, poi regole generiche costruite su segnali del kernel e del
  terminale (`wchan`, eco, modo canonico, schermo alternativo).
- **Profili:**
  - quello di pacman è fornito con `deck`;
  - quello di `ssh-keygen` l'ha scritto, provato e salvato da sola una sessione di Claude Code sulla Deck;
  - una regola di domanda vale solo se finisce sulla riga del cursore.
- **Sicurezza:** l'agente non digita mai segreti. Comandi e risposte passano le regole dell'accesso, ora in
  `agentdeck/access.py`, condivise con la guardia di Claude Code. Il testo del terminale resta nei dati.
- `CLAUDE.md` della Deck indica l'adattatore per i programmi interattivi.
- Controllo dal vivo con otto programmi veri: 20 prove su 20. 201 test.

## 0.4.4 — 2026-10-26

Ciclo 04, task O10.T6: `deck` diventa uno strumento nativo di Claude Code con il server MCP `deck mcp`.

- **Strumenti:** `open` apre qualunque schermata; ogni azione è uno strumento `<componente>_<azione>`, con lo
  schema degli argomenti ricavato dalla specifica dei parametri. Oggi sono 19: `open` e 18 azioni.
- **Risorse:** ogni schermata è anche una risorsa `deck:<indirizzo>`.
- **Stesso motore:** il risultato è la schermata di sempre; le azioni distruttive restano in due passi, con
  anteprima e codice. Descrizioni e istruzioni del server sono solo testo del sistema (INV-4).
- **Sulla Deck:** registrato per l'utente `agent` e permesso dalle impostazioni gestite. Una sessione di
  `claude -p` ha aperto `/status` e chiesto l'anteprima di un rollback senza confermarla.
- **Dal Mac:** `ssh agentdeck deck mcp`, provato con un client JSON-RPC. `.mcp.json` lo offre alle sessioni di
  Claude Code in questo repository.
- `ssh-log.sh` non copia nel journal il flusso JSON-RPC; le chiamate arrivano comunque sullo schermo della Deck.
- Corretto `test_update`: il confronto con `install/install.sh` si salta sulla Deck, dove l'installatore non
  c'è. Prima fermava `deck/install.sh` ai test sulla Deck.
- Fra la 0.4.3 e questa versione, O10.T5 (accesso da fuori casa) è stata chiusa come bloccata in attesa della
  regola sul router: sshguard, scelta automatica LAN o internet in `ssh agentdeck`, Tailscale spento.
- 172 test.

## 0.4.3 — 2026-10-26

Ciclo 04, task O10.T3: cosa sa Claude Code di AgentDeck. Il prompt di sistema per la gestione dell'OS è in
quattro strati, perché le sessioni di Remote Control non accettano le opzioni del prompt di sistema.

- **Identità:** stile di output "AgentDeck", dentro il prompt di sistema.
- **Regole stabili:** `/etc/claude-code/CLAUDE.md`, generato da un modello e dalle 10 invarianti della
  governance, che restano la fonte unica.
- **Vincoli duri:** impostazioni gestite con regole `deny` sui servizi dell'accesso e la modalità senza permessi
  disattivata, più una guardia `PreToolUse` che blocca i comandi che toglierebbero l'accesso.
- **Il momento:** hook `SessionStart` che inietta lo stato della Deck e gli avvisi di `deck status`.
- Sorgenti in `deck/claude/`, installatore `deck/claude/install.sh`.
- Verificato dal vivo con `claude -p` e da una sessione di Remote Control aperta dall'utente:
  - identità, regole e avvisi presenti;
  - regola `deny` e guardia bloccano davvero, anche con Bash permesso;
  - `deck` usato dalla sessione.
- 158 test.

## 0.4.2 — 2026-10-26

Ciclo 04, task O10.T2: Claude Code collegato all'abbonamento e sempre raggiungibile con Remote Control.

- Login fatto dall'utente con l'abbonamento claude.ai (Max). Le credenziali stanno solo sulla Deck, con permessi
  600.
- Prima richiesta senza interfaccia: `claude -p` risponde in 2,3 secondi.
- Nuovo servizio `agentdeck-claude`:
  - `install/agentdeck-claude.service`, installato da `install/claude-service.sh`;
  - avvia `claude remote-control` in una sessione tmux nella cartella di lavoro `~/agentdeck`;
  - è abilitato all'accensione e si riavvia se si ferma.
- Verificato:
  - dopo un riavvio del servizio e dopo un riavvio della Deck si riconnette da solo;
  - nessuna porta nuova in ascolto;
  - l'utente vede la sessione su claude.ai o nell'app.
- Installato `tmux` (snapshot 36-38, servizio con snapshot 40). Proposto il nuovo testo di INV-7, da decidere al
  gate di O10.
- Trappole registrate: P17 (`pkill -f` chiude la propria sessione) e P18 (il codice di login dalla chat non
  arriva).

## 0.4.1 — 2026-10-25

Ciclo 04, task O10.T1: Claude Code installato sulla Deck.

- Nuovo `install/claude-code.sh`, da lanciare come `agent`, mai come root:
  - usa l'installatore ufficiale di Anthropic;
  - verifica la firma GPG del manifest con l'impronta ufficiale della chiave di rilascio, che l'installatore
    non controlla;
  - confronta la checksum del binario installato con il manifest firmato;
  - aggiunge `~/.local/bin` al PATH una volta sola.
- Installata la versione 2.1.310 in 17 secondi, con snapshot 35 prima. `claude doctor` è in ordine, nessuna
  porta nuova in ascolto.
- La prima richiesta vera passa a O10.T2, dopo il login con l'abbonamento (decisione dell'utente).
- Nuovo `docs/claude-code.md`; la procedura di installazione comprende Claude Code.

## 0.4.0 — 2026-10-25

Chiusura del ciclo 03, "Studio dell'architettura agent-first: come funziona il sistema e dove intercettarlo":
2 obiettivi, 7 task completate, 1 bloccata. Roadmap archiviata in `.claude/workflow/roadmaps/`.

- O8 completo: `docs/architettura.md`, con sei strati misurati sulla Deck, 33 presupposti umani, 49 proposte,
  la sintesi e l'esito della revisione con l'utente.
- O9 bloccato: la prova di `deck update` aspetta ancora un aggiornamento vero di Arch e passa al ciclo 04
  (O11).
- Aperto il ciclo 04, "Claude Code dentro AgentDeck: installazione, configurazione e uso reale".
- Debito rimandato, ancora da fare:
  - pulizia degli snapshot e di `@old`;
  - `deck secrets`;
  - rollback dopo un aggiornamento di GRUB;
  - adattatore dei prompt;
  - lettura e modalità compatta dello schermo.

## 0.3.7 — 2026-10-25

Ciclo 03, task O8.T7: sintesi dello studio e revisione con l'utente.

- Sezione 7 di `docs/architettura.md`: 33 presupposti umani in cinque famiglie, i cinque mattoni
  dell'architettura, l'architettura in una pagina, le decisioni e la roadmap proposta.
- Licenza e termini di Claude Code verificati su fonti primarie: modificarlo non è permesso, anche in privato.
- Esito della revisione (sezione 7.4 bis e `PRINCIPI.md`):
  - harness Claude Code senza API di Claude;
  - **il sistema guida l'agente**, che è uno strumento senza cognizione propria;
  - i prompt interattivi restano, tradotti in JSON da un adattatore con profili creati dall'agente;
  - obblighi per ora solo come avvisi;
  - lo sviluppo riparte inserendo Claude Code nel sistema.

## 0.3.6 — 2026-10-25

Ciclo 03, task O8.T6: studio dell'harness dell'agente.

- Sezione 6 di `docs/architettura.md`, verificata su fonti ufficiali di Anthropic.
- Claude Code è proprietario, quindi **un fork non è permesso** dalla licenza.
- Strade permesse:
  - l'Agent SDK, con lo stesso motore;
  - hook, MCP, plugin e skill;
  - la modalità senza interfaccia `claude -p`;
  - Remote Control, che segue una sessione dalla Deck da claude.ai o dal telefono.
- Proposta A6.1: Claude Code non modificato, più un plugin di AgentDeck con `deck mcp`, hook di autoprompting
  e skill; l'Agent SDK per gli agenti nostri. Da decidere in revisione (N21).

## 0.3.5 — 2026-10-25

Ciclo 03, task O8.T5: studio di eventi, log e osservabilità.

- Sezione 5 di `docs/architettura.md`.
- Il journal riceve circa 1.658 righe all'ora: il 28% è la traccia dei comandi dell'agente, e solo il 42% ha un
  identificativo di evento riconoscibile da macchina.
- A riposo il sistema è silenzioso (0 messaggi D-Bus in 8 secondi), e nessuno sveglia l'agente: tutto ciò che
  succede fra una sessione e l'altra si scopre dopo. Il tasto di accensione spegne il server.
- 5 presupposti umani e 9 proposte. Fra queste: `OnFailure=` globale, un raccoglitore di eventi con coda,
  il briefing di inizio sessione `deck inbox`, il risveglio dell'agente per evento, il registro delle azioni.

## 0.3.4 — 2026-10-25

Ciclo 03, task O8.T4: studio dello stato del sistema, del software e degli snapshot.

- Sezione 4 di `docs/architettura.md`.
- Snapshot: 32 in tutto; 19 sono "single" senza pulizia (N15) e le quote di Btrfs sono spente. Sul disco resta
  `@old`. Il log di pacman non torna indietro con un rollback.
- La configurazione di AgentDeck è imperativa: 24 file in `/etc` che nessun pacchetto possiede. pacman non
  vede tutte le modifiche ai file dei pacchetti.
- Già presenti: estensioni `sysext` e `confext` (anche su `/opt`), servizi portabili, `systemd-nspawn`.
- 5 presupposti umani e 8 proposte. Fra queste: una politica degli snapshot, gli stati buoni, lo stato voluto
  dichiarativo con `deck state`, le notizie di Arch come dato, lo strato di AgentDeck fuori dai rollback,
  l'alternativa di un sistema a immagini.

## 0.3.3 — 2026-10-25

Ciclo 03, task O8.T3: studio di identità, permessi, isolamento e segreti dell'agente.

- Sezione 3 di `docs/architettura.md`.
- Oggi:
  - l'agente ha `sudo ALL` senza password e polkit non c'è, quindi ogni API privilegiata è solo per root;
  - i servizi girano senza sandbox (esposizione 9,4-9,6);
  - audit spento, firewall senza regole, nessun archivio di segreti.
- Già pronti: TPM 2.0 con PCR misurati, `systemd-creds`, Landlock e BPF LSM, `systemd-nspawn`.
- 6 presupposti umani e 8 proposte. Fra queste: identità per agente e sessione, un broker dei privilegi al posto
  di `sudo ALL`, `deck secrets` su systemd-creds con il TPM, audit e firewall.

## 0.3.2 — 2026-10-25

Ciclo 03, task O8.T2: studio di init, servizi e interfacce del sistema.

- Sezione 2 di `docs/architettura.md`.
- Sulla Deck ci sono 18 socket varlink di systemd 262, con 27 interfacce: servizi, rete, nomi, journal,
  avvio, credenziali, aggiornamenti. Rispondono in JSON tipizzato in pochi millisecondi. Ci sono anche il D-Bus
  di iwd e molti comandi con uscita JSON.
- `deck` oggi legge testo con 12 parser anche dove esiste un'API, ad esempio per snapper, i servizi e il Wi-Fi.
- 6 presupposti umani (pager, domande interattive, errori in prosa, scoperta da `man`, nessuna traccia
  d'intenzione) e 7 proposte. Fra queste, `deck` sulle API native e AgentDeck esposto come servizio varlink.

## 0.3.1 — 2026-10-25

Ciclo 03, task O8.T1: studio dello strato di avvio, kernel e ripristino.

- Nuovo `docs/architettura.md`: metodo dello studio (come funziona, presupposti umani, punti di intercettazione,
  proposte per livello) e sezione 1.
- Avvio misurato sulla Deck: 20,2 s (firmware 7,0, GRUB 4,2, kernel 6,2, spazio utente 2,8); Secure Boot in
  setup mode, TPM 2.0 presente.
- Presupposti umani trovati:
  - con l'account root bloccato, la shell d'emergenza aspetta un umano alla console e la rete resta spenta;
  - `kernel.panic=0`;
  - watchdog hardware presenti ma inattivi;
  - menu di GRUB solo da tastiera.
- 11 proposte da decidere a fine studio, fra cui l'emergenza raggiungibile via SSH, gli avvii di prova con
  conferma o ritorno automatico, `deck boot` e l'alternativa di systemd-boot con kernel unificati.

## 0.3.0 — 2026-10-25

Chiusura del ciclo 02, "La Deck come server gestito dall'agente: rete, servizi, aggiornamenti, schermo":
4 obiettivi, 4 task completate, 3 bloccate. Roadmap archiviata in `.claude/workflow/roadmaps/`.

- O4 (rete) e O5 (servizi e log) completi: versioni da 0.2.1 a 0.2.4.
- O6 bloccato: `deck update` pronto e installato, manca la prova con un aggiornamento vero di Arch. Riprende
  come O9.T1.
- O7 rinviato dall'utente: lo schermo serve all'umano, la pulizia passa allo studio dello stato (O8.T4).
- Aperto il ciclo 03, "Studio dell'architettura agent-first: come funziona il sistema e dove intercettarlo".
  Prima di altro codice, il sistema si studia strato per strato in `docs/architettura.md`. L'harness degli
  agenti partirà da Claude Code.

## 0.2.4 — 2026-10-25

Ciclo 02, task O5.T2: componente `deck logs`.

- `deck logs` mostra avvisi ed errori dall'avvio; `deck logs query` filtra per unità, periodo (`30m`, `2h`,
  `today`, `boot`, data e ora), gravità e numero di righe. Risultati identici a `journalctl -o json` con gli
  stessi filtri.
- La traccia dei comandi dell'agente scritta dallo schermo resta fuori, salvo `include_agent=true`. `deck` la
  filtra da sé perché `journalctl -T` non funziona con `-o json` (trappola P14).
- Il testo dei log sta solo nei dati: verificato anche dal vivo con una riga malevola scritta con `logger`.
- `deck service show` porta ai log del servizio (`data.logs`); i messaggi d'errore di `deck service` rimandano a
  `deck logs`.
- Controllo dal vivo 11 su 11; 134 test.

## 0.2.3 — 2026-10-25

Ciclo 02, task O5.T1: componente `deck service`.

- `deck service` elenca i servizi di systemd come `systemctl list-units --all`, con abilitazione, conteggi e
  servizi falliti; `deck service show name=…` ne mostra il dettaglio.
- Azioni `start`, `stop`, `restart`, `enable`, `disable`:
  - `stop`, `restart` e `disable` con anteprima e conferma;
  - snapshot prima di `enable` e `disable`;
  - dopo ogni azione lo stato viene riletto e confrontato con quello atteso.
- Protezione dell'accesso: `stop` e `disable` rifiutati per `sshd`, `systemd-networkd`, `iwd`,
  `systemd-resolved` e `dbus-broker` (da cui dipende iwd) e per ciò che richiedono; `restart` di sshd solo
  con la configurazione valida.
- L'avviso `SERVICES_FAILED` di `deck status` ora rimanda a `/service`.
- Controllo dal vivo 28 su 28, con un servizio di prova creato e tolto; 122 test.

## 0.2.2 — 2026-10-25

Ciclo 02, task O4.T2: azioni di rete con anteprima e rete di sicurezza.

- `deck network llmnr_off` (con anteprima, snapshot e verifica di DNS e mDNS) e `llmnr_on` per tornare
  indietro. LLMNR è spento sulla Deck: la porta 5355 non è più in ascolto sulla LAN.
- `deck network prefer_5ghz` passa alla rete a 5 GHz dello stesso router, copiando sulla Deck la password
  della rete attuale senza mostrarla. Il cambio gira in un'unità a parte e torna da solo alla rete di prima
  senza un indirizzo entro 1 minuto o senza `deck network keep_5ghz` entro 3 minuti.
- Provato sulla Deck:
  - ritorno automatico senza conferma, 5 secondi dopo la scadenza;
  - cambio confermato, con riavvio di iwd e riavvio della Deck: resta sui 5 GHz, IP .49, `ssh agentdeck` ok;
  - 585 Mbit/s in trasmissione contro 144.
- Trovato e corretto: iwd si collega solo a reti viste da una sua scansione (P12). Le reti nascoste del
  router non contano più come reti sorelle.
- `install/install.sh` spegne LLMNR e dà a iwd la preferenza per i 5 GHz. Controllo dal vivo 11 su 11;
  100 test.

## 0.2.1 — 2026-10-25

Ciclo 02, task O4.T1: componente `deck network` (riprende N8).

- Interfacce, Wi-Fi collegato e reti visibili per banda: cache del kernel nella schermata, scansione fresca
  con `deck network scan` (circa 5 secondi).
- Reti sorelle dello stesso router; DNS, mDNS e LLMNR da `resolvectl`; porte in ascolto.
- Gli avvisi `WIFI_BAND_2G` e `LLMNR_LISTENING`, in `deck status` e `deck network`, puntano alle azioni di
  `/network`, che restano non disponibili fino a O4.T2.
- Scoperto: i 5 GHz di casa sono una rete distinta, "… - 5Ghz". Controllo dal vivo: 11 valori su 11; 80 test.

## 0.2.0 — 2026-10-25

Chiusura del ciclo 01, "Prima interfaccia agentica: protocollo, stato e snapshot": 3 obiettivi, 12 task,
nessun blocco. Roadmap archiviata in `.claude/workflow/roadmaps/`. Aperto il ciclo 02, "La Deck come server
gestito dall'agente: rete, servizi, aggiornamenti, schermo".

- O1: base operativa affidabile.
  - Repository privato con identità personale e una versione pubblicata per ogni task.
  - IP stabile e accesso SSH al primo tentativo.
  - Documentazione per argomento.
- O2: protocollo dell'interfaccia agentica approvato (`docs/protocollo.md`) e motore `deck` sulla Deck.
- O3: `deck status`, `deck snapshot` con rollback provato, schermo della Deck con comandi e risposte.

## 0.1.12 — 2026-10-25

Ciclo 01, task O3.T3: rollback con anteprima e conferma.

- `deck snapshot rollback id=N` mostra prima un'anteprima: pacchetti rimossi, che tornano o che cambiano
  versione, controllo dell'accesso SSH e della versione di GRUB nello snapshot di destinazione.
- Con il codice di conferma: salva lo stato attuale come snapshot, sostituisce il subvolume `@` con una copia
  dello snapshot (rimettendo subito tutto com'era se un passo fallisce) e riavvia dopo 10 secondi.
- Rifiuta gli snapshot da cui la Deck ripartirebbe senza accesso SSH o con un GRUB diverso.
- Prova reale sulla Deck: modifica di prova annullata, Deck tornata in 44 secondi, stato precedente
  recuperabile nello snapshot 18. 67 test.

## 0.1.11 — 2026-10-25

Ciclo 01, task O3.T2: componente `deck snapshot`, elenco e creazione.

- `deck snapshot` elenca gli snapshot come snapper e indica per ognuno se è avviabile dal menu di GRUB
  (`in_grub`, `null` mentre grub-btrfsd riscrive il menu).
- `deck snapshot create description="…"` crea uno snapshot singolo, marcato `source: deck`.
- Il rollback compare tra le azioni come non ancora disponibile.
- Verificato sulla Deck: elenco identico a snapper; lo snapshot creato da `deck` è comparso nel menu di
  GRUB dopo 7 secondi. 56 test.

## 0.1.10 — 2026-10-25

Ciclo 01, task O3.T5: sullo schermo della Deck anche la risposta di ogni comando (richiesta dell'utente).

- Sotto ogni comando compare il suo output, con gli errori in rosso; le righe lunghe vanno a capo su al
  massimo 3 righe; la risposta JSON di `deck` è sostituita dalla riga di esito.
- Lo script di registrazione fa passare stdout e stderr da `tee`: chi lancia il comando riceve esattamente
  gli stessi dati, codice di uscita compreso (verificato con dati binari a ogni installazione). Esclusi i
  trasferimenti di file e le sessioni con terminale.
- Rete di sicurezza estesa: le versioni precedenti dello script e della configurazione SSH tornano da sole
  dopo 3 minuti se le prove falliscono.

## 0.1.9 — 2026-10-25

Ciclo 01, task O3.T4: schermo della Deck come terminale dell'agente (richiesta dell'utente).

- Al posto del login su `tty1` lo schermo mostra in tempo reale ogni comando SSH dell'agente e l'esito di
  ogni chiamata a `deck`, con testo ripulito e segreti oscurati.
- Comandi registrati tramite `BASH_ENV` per l'utente `agent`: autenticazione SSH invariata, e un errore
  nello script di registrazione non blocca i comandi.
- Installazione con snapshot e rete di sicurezza SSH (ripristino automatico in 3 minuti se `ssh`, `scp` o
  `rsync` non funzionano dopo la modifica). 42 test; documentazione in `docs/schermo.md`.

## 0.1.8 — 2026-10-25

Ciclo 01, task O3.T1: componente `deck status`.

- Stato della macchina in una schermata: sistema, hardware, carico, batteria, temperature, memoria, disco,
  rete e Wi-Fi, porte in ascolto, servizi, snapshot, sincronizzazione dell'ora.
- Avvisi con codici stabili: oggi segnala Wi-Fi a 2,4 GHz, LLMNR superfluo sulla LAN e ventola non leggibile.
- Letture robuste in `agentdeck/system.py`: una lettura che fallisce non rompe la schermata.
- Controllo dal vivo: 23 valori su 23 coincidono con gli strumenti classici di Linux; 34 test verdi.
- Installato `iw` sulla Deck (snapshot 8 e 9) e aggiunto all'elenco pacchetti di `install/install.sh`.

## 0.1.7 — 2026-10-25

Ciclo 01, task O2.T2: motore `deck` e installazione sulla Deck.

- `deck` implementa il protocollo v1:
  - schermate validate prima di ogni risposta;
  - canale istruzioni protetto: solo testo `SysText` con valori validati;
  - navigazione per indirizzi, parametri tipizzati;
  - conferme con codice (5 minuti, una volta sola);
  - errori strutturati con vie d'uscita.
- Componenti: `/` (schermata principale) e `/protocol` (il protocollo descritto all'agente).
- 22 test (conformità, iniezione nel canale istruzioni, parametri, conferme, guasti), verdi sul Mac e
  sulla Deck; una chiamata dura circa 0,09 secondi sulla Deck.
- Installazione ripetibile con `deck/install.sh` in `/opt/agentdeck`; documentazione in `docs/deck.md`.

## 0.1.6 — 2026-10-25

Ciclo 01, task O2.T1: specifica del protocollo di schermata e autoprompting.

- `docs/protocollo.md`, approvato: ogni risposta di `deck` è una schermata JSON con dati, azioni,
  navigazione, avvisi, errori, conferme con anteprima e istruzioni per l'agente (autoprompting).
- Regole di sicurezza del canale istruzioni (INV-4) e 8 esempi con dati reali della Deck.
- Decisioni: Python 3 con la sola libreria standard; testi per l'agente in inglese.

## 0.1.5 — 2026-10-25

Ciclo 01, task O1.T5: accesso SSH affidabile dal Mac.

- `ssh agentdeck` punta all'IP stabile `192.168.1.49` invece che al nome `agentdeck.local`, che dal Mac a
  volte non si risolve. Il nome resta disponibile come `ssh agentdeck-mdns`.
- `HostKeyAlias agentdeck`: l'identità della Deck si controlla sotto un solo nome, qualunque indirizzo si usi.
- Verificato con 10 collegamenti consecutivi riusciti al primo tentativo; `docs/accesso.md` aggiornato.
- Contatore delle versioni della governance riallineato: era rimasto indietro di una versione.

## 0.1.4 — 2026-10-25

Ciclo 01, task O1.T4: documentazione di base, indicizzata e collegata al codice.

- `README.md` del progetto e indice `docs/README.md`.
- Documenti per argomento: hardware, chiavetta live, installazione, accesso alla Deck, sviluppo
  (repository, versioni, pubblicazione, governance).
- `PRINCIPI.md`: principio del livello di intervento (INV-10) e decisioni del 25/10.
- Ogni script in `live/` e `install/` rimanda al suo documento, e ogni documento agli script.

## 0.1.3 — 2026-10-25

Ciclo 01, task O1.T3: comandi di base attesi dagli agenti.

- Installato `inetutils` sulla Deck: ora `hostname` è disponibile e restituisce `agentdeck`.
- Snapshot automatici prima e dopo l'installazione (snap-pac).
- Pacchetto aggiunto all'elenco di `install/install.sh`.

## 0.1.2 — 2026-10-25

Ciclo 01, task O1.T2: IP stabile della Deck sulla rete di casa.

- `SendRelease=no` nella configurazione DHCP (Wi-Fi e cavo): allo spegnimento la Deck non restituisce
  l'indirizzo e il router le riassegna lo stesso. Prima ogni riavvio portava all'IP successivo.
- Verificato con due riavvii consecutivi: IP sempre `192.168.1.49`, `ssh agentdeck` al primo tentativo.
- Correzione riportata in `install/install.sh`.

## 0.1.1 — 2026-10-25

Ciclo 01, task O1.T1: identità git personale e remote privato su GitHub.

- Identità git personale (Davide, davideditrani94@gmail.com) impostata solo per questo repository;
  autore corretto anche sul primo commit.
- Repository privato `panicDa3m0n/agentdeck` con `main` e tag di versione.
- Credential helper locale: il repository pubblica sempre come `panicDa3m0n`, qualunque account `gh` sia attivo.

## 0.1.0 — 2026-10-25

Installazione base e governance del progetto.

- Principi del progetto (PRINCIPI.md).
- Chiavetta live di Arch con Wi-Fi e SSH automatici (`live/`).
- Installazione di Arch sulla Steam Deck a fasi (`install/`): Btrfs con snapshot, GRUB + grub-btrfs,
  utente `agent` con accesso solo via chiave.
- Behaviour Governance: dossier, 10 invarianti, roadmap del ciclo 01.
