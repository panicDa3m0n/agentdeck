# Interfacce effimere sullo schermo della Deck

AgentDeck è un sistema per agenti: l'umano non lo gestisce e non ha un'interfaccia permanente. Quando c'è qualcosa
da vedere o da decidere, sullo schermo della Deck compare un'interfaccia **effimera**, fatta per la **minima
interazione umana**, che poi sparisce. Questo documento fissa lo stile di queste interfacce e la tecnologia
grafica, decisi con l'utente il 27/10/2026 (ADR-0003, obiettivo O15).
Indice: [README.md](README.md).

## Le regole dello stile

Valgono per ogni interfaccia dello schermo, presente e futura.

1. **Calmo di base.** Lo schermo è scuro, con una sola riga di stato (nome, indirizzo, sessioni attive, avvisi);
   dopo un po' di inattività la luce si abbassa.
2. **Effimero.** Un'interfaccia compare per un tocco o un pulsante, oppure quando il sistema ha qualcosa da far
   decidere all'umano. Sparisce dopo la scelta, o dopo 60 secondi senza tocchi, e lo schermo torna calmo.
3. **Interazione minima.** Al massimo 3 o 4 scelte grandi, con quella consigliata già evidenziata; niente da
   scrivere, niente impostazioni. Funziona con il tocco e con i pulsanti: A conferma, B torna indietro, la croce
   sposta la selezione.
4. **Le stesse azioni dell'agente.** Ogni pulsante chiama un'azione di `deck` ([protocollo.md](protocollo.md)); le
   azioni che chiudono o cancellano qualcosa chiedono una seconda pressione, come l'anteprima con il codice di
   conferma. L'interfaccia non ha una logica sua: è una vista di una schermata di `deck`.
5. **Traccia.** Ogni scelta fatta sullo schermo finisce nel registro come un'azione, e l'agente ne riceve l'esito.
6. **Solo locale.** Le pagine sono servite da `deck` su 127.0.0.1: nessuna porta si apre verso la rete (INV-5). Il
   testo esterno, per esempio il titolo di una sessione, si mostra sempre come testo, mai come codice della pagina
   (INV-4).
7. **Niente più terminale sullo schermo.** I comandi dell'agente non scorrono più sullo schermo
   ([schermo.md](schermo.md)): l'attività resta nel registro del sistema.

## La tecnologia

- **Compositore:** [cage](https://github.com/cage-kiosk/cage) (0.3.1 su Arch, wlroots 0.20), un compositore
  Wayland che mostra una sola applicazione a schermo intero. Prende il posto del terminale su `tty1`.
- **Motore della pagina:** Chromium in modalità kiosk, nativo Wayland, che apre solo le pagine locali di `deck`.
- **Le pagine:** `deck` trasforma una sua schermata (JSON, protocollo v1) in una pagina: dati, scelte e azioni
  diventano testo e pulsanti. Così ogni componente di `deck` ha la sua interfaccia senza lavoro su misura, e in
  futuro l'agente potrà scrivere una pagina al volo quando ha qualcosa da mostrare.
- **Comandi:** lo schermo tattile (`FTS3528`) e il gamepad della Deck (`Steam Deck`, `js0`: A, B, X, Y, croce)
  arrivano al browser, il primo come tocco e il secondo con l'API Gamepad; il controller in modalità
  tastiera e mouse resta disponibile.
- **Peso:** 112 pacchetti nuovi, circa 250 MB da scaricare, misurati il 27/10/2026 con `pacman -Sp` sulla Deck.
  Fra questi ci sono i driver grafici (mesa), che prima non erano installati.

Da verificare quando si costruisce lo schermo (O15.T3):
- l'orientamento: il pannello è 800×1280, montato in verticale ([hardware.md](hardware.md)), e la console oggi
  appare già in orizzontale;
- che il gamepad della Deck arrivi a Chromium con l'API Gamepad;
- come si abbassa la luce (`/sys/class/backlight`) e come si spegne lo schermo quando è calmo;
- che, se `cage` o Chromium non partono, lo schermo torni a un terminale e l'accesso SSH non cambi mai (INV-1).

## La decisione (ADR-0003)

**Contesto.** Il 27/10/2026 l'utente ha chiesto una rapida interfaccia per vedere le sessioni Claude della Deck,
chiuderle e aprirne di nuove, e di farne il primo esempio di interfacce effimere e di minima interazione umana. Ha
precisato che serve solo sullo schermo della Deck, al posto del terminale che mostrava i comandi dell'agente. Fino
ad allora lo schermo era un dettaglio rimandato ([architettura.md](architettura.md), 7.3).

**Opzioni valutate**, con i pesi misurati sulla Deck:

| Opzione | Pacchetti nuovi | Da scaricare | Pro e contro |
|---|---|---|---|
| Console di Linux, Python standard, tocco e pulsanti letti da `/dev/input` | 0 | 0 | Nessun componente nuovo (INV-10), ma solo testo e caratteri di disegno |
| **cage + Chromium in kiosk** | 112 | 250 MB | Pagine HTML: generiche dalle schermate di `deck`, scrivibili al volo dall'agente; tocco e gamepad nativi. Più pesante, aggiornamenti frequenti |
| cage + app GTK4 in Python | 115 | 123 MB | App nativa senza server, più leggera; ogni interfaccia va programmata, stile limitato al CSS di GTK |
| cage + WPE WebKit | 88 | 140 MB | Motore leggero, ma su Arch manca il programma che lo lancia (`cog`): andrebbe compilato |

**Decisione.** L'utente ha scelto la grafica invece della console, poi cage con Chromium e le sette regole dello
stile così come sono scritte sopra. Il motivo: un'interfaccia effimera che l'agente può creare al volo è
naturalmente una pagina, e una sola strada copre sia le schermate di `deck` sia le pagine generate.

**Conseguenze.**
- È una sostituzione di componenti, decisa esplicitamente dall'utente (INV-10): un compositore e un browser sulla
  Deck, per la prima volta.
- Lo schermo con i comandi dell'agente ([schermo.md](schermo.md)) sarà sostituito in O15.T3; la registrazione
  dei comandi nel registro resta.
- INV-2 resta intatta: l'interfaccia grafica è per l'umano, e ogni sua azione esiste anche per gli agenti, in
  `deck`, via CLI e MCP. Per le sessioni Claude è la schermata `deck claude` (O15.T2).
- INV-5: il server delle pagine ascolta solo su 127.0.0.1.
- INV-3: prima di installare i pacchetti grafici serve uno snapshot.

**In parole semplici.** Lo schermo della Deck smette di mostrare i comandi dell'agente e diventa scuro e calmo.
Quando lo tocchi, o quando il sistema ha qualcosa da chiederti, compare una schermata semplice con pochi pulsanti
grandi, e poi sparisce. La prima serve a vedere, aprire e chiudere le sessioni Claude.

## La prima interfaccia: le sessioni Claude

### La schermata `deck claude` (O15.T2)

È la base dell'interfaccia: la usano l'agente (strumenti MCP `claude_open` e `claude_close`, oppure
`mcp__deck__open` con `path=/claude`), il Mac (`ssh agentdeck deck claude`) e, in O15.T3, lo schermo.
Codice: [../deck/agentdeck/claude_sessions.py](../deck/agentdeck/claude_sessions.py) e
[../deck/agentdeck/components/claude.py](../deck/agentdeck/components/claude.py); test:
[../deck/tests/test_claude_sessions.py](../deck/tests/test_claude_sessions.py).

| Azione | Effetto | Cosa fa |
|---|---|---|
| (schermata) | read | `data.sessions`: per ogni sessione viva `id`, `title`, `state` (`busy` al lavoro, `idle` in attesa, `starting` appena aperta), `started`, `folder`, `app_url` (il link per l'app Claude), `pid`, `memory_mb`, `opened_by_deck`, `this_session` |
| `open name=<nome>` | safe | Apre una sessione nuova con Remote Control nella cartella `~/agentdeck/sessioni/<nome>`; compare nell'app Claude con quel nome. Al più 8 sessioni aperte da `deck` |
| `close id=<id>` | destructive | Anteprima con la sessione e il codice di conferma; poi SIGINT al processo, e SIGTERM se dopo 10 secondi gira ancora. Mai la sessione da cui arriva la chiamata |

**Come funziona**, verificato sulla Deck il 27/10/2026 con Claude Code 2.1.310:
- **Elenco.** Claude Code scrive una scheda per ogni sessione in `~/.claude/sessions/<pid>.json`: titolo, stato,
  cartella, id per l'app (`bridgeSessionId`) e istante di avvio del processo (`procStart`). `deck` tiene solo le
  schede il cui processo è vivo e ha lo stesso istante di avvio (campo 22 di `/proc/<pid>/stat`): un PID riusato da
  un altro processo non diventa mai una sessione da chiudere. I file `.key` accanto alle schede non si leggono.
- **Apertura.** Remote Control accetta un solo server per cartella ("This folder is already served by a terminal
  `claude remote-control`"), e `~/agentdeck` ha già quello del servizio `agentdeck-claude`. Per questo ogni
  sessione nuova ha una sottocartella sua e un server che tiene una sola sessione ed esce quando lei finisce
  (`claude remote-control --name <nome> --spawn session`, nella sessione tmux `rc-<nome>`). La fiducia nella
  cartella viene da `~/agentdeck`. Se il server non parte, `data.output` riporta le sue ultime righe.
  Riaprire con un nome già usato ha riportato lo stesso id nell'app (`session_…`).
- **Chiusura.** SIGINT chiude la sessione in modo pulito, anche dentro il server con più sessioni di
  `~/agentdeck`, che resta pronto; SIGTERM la chiude come errore ("Session failed"), ed è solo il ripiego. La
  trascrizione e i file restano; la cartella di una sessione aperta da `deck` resta, con quello che la sessione ci ha
  scritto.

Prova sulla Deck del 27/10/2026: aperta e chiusa la sessione `prova-o15t2` con `deck claude`, mentre le due sessioni
al lavoro restavano attive con gli stessi PID.

### Lo schermo (O15.T3)

Installato il 27/10/2026 al posto del terminale dell'agente.

**Cosa vede chi ha la Deck in mano:**
- **Calmo:** schermo nero con una riga di stato in basso, per esempio
  `agentdeck · 192.168.1.49 · 2 sessioni, 1 al lavoro · 23:08`, aggiornata ogni 30 secondi. Dopo 2 minuti senza
  tocchi la luce scende all'8%; il primo tocco la rialza.
- **Sessioni:** un tocco qualsiasi, oppure A, Y o Menu del gamepad, apre l'interfaccia. In alto c'è "Apri una
  sessione nuova", già selezionato; sotto, una scheda per sessione con titolo, stato colorato (al lavoro, in attesa,
  in avvio) e ora di inizio, e il pulsante "Chiudi". La sessione da cui arriverebbe la chiamata è "In uso" e non si
  chiude.
- **Aprire:** il nome lo sceglie il sistema (`sessione-<ora><minuti>`), niente da scrivere. Dopo qualche secondo
  compare "Sessione … aperta. La trovi nell'app Claude."
- **Chiudere:** la prima pressione su "Chiudi" chiede l'anteprima a `deck` e trasforma il pulsante in "Conferma",
  con un avviso se la sessione è al lavoro; la seconda pressione, entro 10 secondi, chiude.
- **Sparire:** dopo una scelta compare un messaggio per 4 secondi, poi lo schermo torna calmo; senza tocchi per
  60 secondi l'interfaccia sparisce da sola (il conto alla rovescia è in basso). B o "Indietro" la chiudono subito.
- **Comandi:** tocco; gamepad con la disposizione standard (A conferma, B indietro, croce per spostare la
  selezione); tastiera con frecce, Invio ed Esc.

**Come è fatto:**

| Pezzo | Cosa fa |
|---|---|
| [../deck/ui/index.html](../deck/ui/index.html) | La pagina: vista calma, sessioni, messaggi; tocco, tasti e gamepad; tempi. Il testo che arriva da `deck` entra solo come testo (`textContent`) |
| [../deck/agentdeck/ui.py](../deck/agentdeck/ui.py) | `deck ui`: serve la pagina e l'API su 127.0.0.1:8790. Le azioni passano per `deck` con anteprima e conferma, e vanno nel registro come le altre chiamate (identificatore `agentdeck`). Allo schermo arriva solo `/claude` |
| [../deck/ui/agentdeck-ui-server.service](../deck/ui/agentdeck-ui-server.service) | Servizio del server, utente `agent`. A ogni avvio un codice nuovo in `/run/agentdeck-ui.token` (640, `agent:deckui`) |
| [../deck/ui/agentdeck-ui.service](../deck/ui/agentdeck-ui.service) | Servizio dello schermo su `tty1`, utente `deckui` senza privilegi: `cage` con Chromium in kiosk. Se il server riparte, riparte anche lui con il codice nuovo |
| [../deck/ui/pam-agentdeck-ui](../deck/ui/pam-agentdeck-ui) | `/etc/pam.d/agentdeck-ui`: la sessione di logind che dà a cage il seat, lo schermo e i comandi |
| [../deck/ui/kiosk.sh](../deck/ui/kiosk.sh) | Dentro cage: ruota l'uscita `eDP-1` (trasformazione `270`, modificabile con `AGENTDECK_UI_TRANSFORM`) e avvia Chromium con il codice nell'ancora dell'indirizzo |
| [../deck/ui/install-ui.sh](../deck/ui/install-ui.sh) | Installazione ripetibile, lanciata da `deck/install.sh`: snapshot, pacchetti (`cage`, `chromium`, `wlr-randr`, `grim`), utente, PAM, servizi |

**Sicurezza:**
- il server ascolta solo su 127.0.0.1 e accetta solo l'host locale; l'API vuole il codice, che hanno solo `agent`
  e `deckui`: un servizio dell'utente sulla Deck non può aprire o chiudere sessioni;
- Chromium gira come `deckui`, che non ha `sudo` né password; la pagina non carica nulla da fuori (politica di
  sicurezza `default-src 'none'`);
- SSH, rete e registrazione dei comandi non cambiano (INV-1).

**Ripiego:** il terminale dell'agente ([schermo.md](schermo.md)) resta installato ma spento. Se lo schermo grafico
fallisce 5 volte in 2 minuti, systemd riaccende il terminale (`OnFailure`). Per tornarci a mano:
`sudo systemctl disable --now agentdeck-ui agentdeck-ui-server && sudo systemctl enable --now agentdeck-screen`.

**Guardare lo schermo senza esserci:** dentro cage, come `deckui`:

```bash
ssh agentdeck 'sudo -u deckui env XDG_RUNTIME_DIR=/run/user/$(id -u deckui) WAYLAND_DISPLAY=wayland-0 grim /tmp/schermo.png'
```

**Verifiche del 27/10/2026:**
- servizi attivi, sessione di logind `deckui` su `seat0`/`tty1`, server solo su 127.0.0.1:8790;
- screenshot con `grim`: pagina in orizzontale, vista calma con la riga di stato;
- API dal vivo: senza codice risponde 401; aperta la sessione `sessione-prova` (registrata nell'app in 5
  secondi), anteprima e chiusura con SIGINT dopo 20 secondi; luce all'8% e di nuovo piena;
- le due sessioni al lavoro restano attive con gli stessi PID;
- l'installazione ha aperto 47 obblighi `PROFILE_NEEDED` per i pacchetti nuovi e le loro dipendenze: chiusi con il
  motivo, perché nessuno di quei programmi si usa in modo interattivo (annotazione N65).

**Da sapere:**
- Chromium proponeva di tradurre la pagina dall'italiano: la pagina dichiara `translate="no"` e Chromium parte con
  `--lang=it`.
- Una sessione appena aperta cambia processo quando si registra nell'app (trappola P24): per questo `open` aspetta
  la registrazione e le sessioni aperte da `deck` hanno un id preso dalla loro cartella.
