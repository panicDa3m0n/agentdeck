# L'adattatore dei programmi interattivi: `deck term`

Molti programmi guidano chi li usa con domande: conferme `[Y/n]`, menu numerati, richieste di un percorso, pager.
È autoprompting nativo, e non si può strutturare programma per programma. L'adattatore, deciso il 25/10/2026
([architettura.md](architettura.md), 7.4 bis), traduce in JSON per l'agente ciò che il terminale mostra a una
persona. Così l'agente usa una moltitudine di programmi senza codice su misura per ciascuno (task O10.T7).

Codice:
- [../deck/agentdeck/term.py](../deck/agentdeck/term.py): backend tmux, stato del processo e del terminale,
  riconoscimento delle domande, profili, sessioni;
- [../deck/agentdeck/components/term.py](../deck/agentdeck/components/term.py): la schermata `/term` e le sue azioni;
- [../deck/profiles/](../deck/profiles/pacman.json): i profili forniti con `deck`.

Test: [../deck/tests/test_term.py](../deck/tests/test_term.py), con tmux finto, e
[../deck/tests/live_term_check.py](../deck/tests/live_term_check.py), con programmi veri sulla Deck.
Indice: [README.md](README.md).

## Come si usa

```bash
deck term start command="sudo pacman -S cowsay"     # parte e aspetta la prima domanda (al più 5 secondi)
deck term choose id=1a2b option=n                   # risponde scegliendo una delle opzioni riconosciute
deck term show id=1a2b                              # la schermata della sessione, adesso
deck term close id=1a2b                             # anteprima, poi confirm=<codice>
```

Da Claude Code sono gli strumenti `mcp__deck__term_start`, `mcp__deck__term_choose` e così via
([deck.md](deck.md), "Server MCP").

| Azione | Effetto | Cosa fa |
|---|---|---|
| `start command= [cwd=] [wait_s=]` | safe | Avvia il comando in un terminale nuovo; aspetta la prima domanda, l'uscita o fino a `wait_s` (1-30, predefinito 5) |
| `show id=` | read | La schermata della sessione |
| `answer id= text= [enter=]` | safe | Digita il testo; poi Invio, salvo `enter=false` |
| `choose id= option=` | safe | Sceglie una chiave di `data.question.options`: per conferme e menu digita la chiave e Invio, per i pager preme il tasto |
| `key id= key= [repeat=]` | safe | Preme un tasto fra quelli elencati in `data.keys` (Invio, frecce, Esc, Tab, Ctrl-C, Ctrl-D…) |
| `wait id= [seconds=]` | read | Aspetta fino a 60 secondi che il programma chieda qualcosa, esca o resti fermo |
| `interrupt id=` | safe | Manda Ctrl-C |
| `close id=` | destructive | Chiude la sessione, e termina il programma se gira ancora: anteprima e conferma |
| `profile_save profile=` | safe | Salva il profilo di un programma, in JSON |
| `profile_show program=` | read | Mostra il profilo di un programma |
| `profile_test id= [profile=]` | read | Prova un profilo, salvato o in bozza, sullo schermo attuale di una sessione |

Le azioni che aspettano (`start`, `wait` e quelle che inviano tasti) durano fino al tempo indicato: sono
l'eccezione alla regola del protocollo di rispondere entro un secondo.

## La schermata di una sessione

`term.session`, con i campi della proposta del 25/10:

| Campo | Contenuto |
|---|---|
| `data.session` | `id`, `command`, `program`, `state`, `exit_status`, `exit_signal`, `started`, `duration_s`, `idle_s`, `foreground` (PID, nome, `waiting_on` del processo in primo piano), `alternate_screen` |
| `data.terminal` | `cols` e `rows` (160 × 48), `cursor`, `echo` e `canonical` del terminale, `lines` (lo schermo visibile), `new_lines` (le righe comparse dall'ultima lettura, al più 200) |
| `data.question` | `text`, `type`, `options` (chiave ed etichetta), `default`, `origin` (la regola che l'ha riconosciuta), `fields` (i gruppi nominati della regola del profilo) |
| `data.parsed` | I dati che il profilo estrae dall'output |
| `data.profile` | Il profilo usato e la sua origine, `agent` o `builtin` |
| `prompt` | L'istruzione per lo stato e il tipo di domanda: come rispondere, cosa leggere prima |

**Stati:**
- `running`: il programma lavora;
- `waiting_input`: fermo da almeno mezzo secondo, con una domanda;
- `stalled`: nessuna uscita da 30 secondi, e il programma non sta leggendo dal terminale;
- `exited`: il programma è uscito, con il suo codice.

**Tipi di domanda:** `confirm`, `choice`, `text`, `secret`, `menu`, `pager`, `unknown`.

La schermata `/term` elenca le sessioni aperte, al più 8, e i profili, e mette il formato dei profili in
`data.profile_format`. Ha tre avvisi:
- `TERM_WAITING_SECRET`: una sessione chiede un segreto;
- `TERM_STALLED`: una sessione è ferma;
- `TERM_UNRECOGNIZED`: una sessione aspetta una domanda non riconosciuta, per un programma senza profilo.

## Come funziona

- **Un terminale che vede solo l'agente.** Ogni sessione è una sessione tmux `adp-<id>`, su un server tmux tutto
  suo (`tmux -L agentdeck-term`), separato da quello di Claude Code. La configurazione (`remain-on-exit`, senza
  la riga "Pane is dead", barra di stato spenta) sta in `~/.local/state/agentdeck/term/tmux.conf`. Accanto c'è
  lo stato di ogni sessione, per sapere quali righe l'agente ha già visto.
- **Segnali del kernel e del terminale**, verificati sulla Deck il 26/10/2026:
  - il processo in primo piano che legge dal terminale dorme in `wait_woken`, o in `poll_schedule_timeout` per i
    programmi con readline, letto da `/proc/<pid>/wchan`. Il kernel aggiunge suffissi come `.constprop.0`, che
    si tolgono prima del confronto (trappola P21). `/proc/<pid>/syscall` non è leggibile (Yama
    `ptrace_scope=1`);
  - nei programmi con più thread (Go, come `gh`) il thread principale aspetta gli altri in `futex_do_wait` e la
    lettura dal terminale sta in un altro thread: se il thread principale non aspetta il terminale, conta un
    thread qualsiasi in `wait_woken` o `n_tty_read` (`/proc/<pid>/task/*/wchan`). Le attese in poll ed epoll degli
    altri thread non contano, perché un programma Go ne ha sempre una per la rete (trappola P23);
  - il terminale canonico senza eco (`icanon -echo`) vuol dire una password;
  - un programma a tutto schermo spegne il modo canonico e di solito usa lo schermo alternativo;
  - un editor di riga come readline spegne eco e modo canonico senza schermo alternativo: resta un prompt di riga.
- **Riconoscimento:** prima il profilo del programma, poi le regole generiche:

| Regola generica (`origin`) | Quando |
|---|---|
| `generic:echo-off` | Terminale canonico senza eco: `secret` |
| `generic:pager` | `(END)`, `--More--` o `:` in fondo a un programma non canonico: `pager`, opzioni `space` e `q` |
| `generic:fullscreen` | Schermo alternativo senza un pager riconosciuto: `unknown` |
| `generic:secret-word` | Il prompt nomina una password, passphrase, PIN o token e finisce con `:` |
| `generic:yes-no` | `[Y/n]`, `(y/N)`, `(yes/no)`: `confirm`; la maiuscola dà il predefinito |
| `generic:numbered` | Righe `1) …` o `1. …`, anche più opzioni su una riga, sopra un prompt: `choice` |
| `generic:prompt` | Prompt che finisce con `:`, `?`, `>`, `#` o `$`: `text` |
| `generic:waiting`, `generic:no-prompt` | Il programma aspetta ma la domanda non si riconosce: `unknown` |

## I profili

Un profilo insegna all'adattatore le domande di un programma e i dati da estrarre. **Li scrive l'agente**, dentro il
sistema, con `deck term profile_save`; li prova prima con `profile_test`.

```json
{"program": "ssh-keygen", "description": "…", "author": "agent",
 "questions": [{"id": "file", "pattern": "Enter file in which to save the key \\((?P<default>[^)]*)\\):\\s*$",
                "type": "text"},
               {"id": "passphrase", "pattern": "Enter passphrase.*:\\s*$", "type": "secret"}],
 "parse": [{"name": "fingerprint", "pattern": "^(?P<hash>SHA256:\\S+) (?P<comment>.*)$"}]}
```

- **Regole di domanda:**
  - espressioni regolari di Python, cercate nelle ultime 8 righe non vuote fino al cursore. Una regola vale solo
    se la corrispondenza **finisce sulla riga del cursore**, cioè sulla domanda in corso: una domanda già
    risposta, ancora visibile sopra, non vince;
  - vince la prima regola che vale. I gruppi nominati vanno in `question.fields`, un gruppo `default` dà il
    predefinito;
  - `options` elenca opzioni fisse, `options_pattern` le estrae con i gruppi `key` ed eventualmente `label`.
- **Regole di estrazione** (`parse`): cercate in tutto l'output. I gruppi nominati vanno in
  `data.parsed.<nome>`; con `all: true` si tengono tutte le corrispondenze.
- **Dove stanno:**
  - i profili scritti dall'agente in `~/.local/share/agentdeck/profiles/<programma>.json` dell'utente `agent`.
    Stanno in `@home`, quindi un rollback del sistema non li cancella;
  - quelli forniti con `deck` in `/opt/agentdeck/profiles/`;
  - a parità di programma vince quello dell'agente. Un profilo non valido viene ignorato.
- **Il programma** si ricava dal comando, saltando assegnazioni di variabili e involucri come `sudo`, `env`, `nice`
  e `timeout` con le loro opzioni.
- **Profili presenti:**
  - `pacman`, fornito con `deck`: installazione, rimozione, sostituzioni, conflitti, chiavi, scelta del fornitore,
    pulizia della cache; estrae pacchetti, dimensioni, errori e avvisi;
  - `ssh-keygen`, **scritto dall'agente sulla Deck** il 26/10/2026 (vedi "Verifiche").

## Sicurezza

- **I segreti non li digita mai l'agente.** Con una domanda `secret`, `answer` e `choose` sono rifiutati, e `key`
  ammette solo Ctrl-C, Ctrl-D ed Esc per uscire. La schermata dice di chiedere al proprietario. Il riferimento a un
  segreto custodito dal sistema arriverà con `deck secrets` (A3.6).
- **L'accesso resta protetto (INV-1).** Il comando di `start` e il testo di `answer` passano le stesse regole della
  guardia dei comandi Bash ([../deck/agentdeck/access.py](../deck/agentdeck/access.py)): `deck term` non diventa
  una scorciatoia per fermare sshd o spegnere il Wi-Fi.
- **Il testo del terminale è un dato (INV-4).** Righe, comando, domanda, opzioni e campi estratti stanno solo in
  `data`; titoli e prompt contengono solo l'id della sessione e valori fissi. I test lo verificano con testo
  malevolo dentro il terminale, il menu e il programma.
- **Le risposte sono dell'agente.** L'adattatore non conosce le conseguenze di una risposta: il prompt chiede di
  leggere la domanda per intero. Per i pacchetti, snap-pac fa uno snapshot prima e dopo ogni transazione.

## Verifiche del 26/10/2026

- **Controllo dal vivo sulla Deck**, `python /opt/agentdeck/tests/live_term_check.py`, 20 prove su 20:
  - `input()` di Python come testo;
  - `getpass` come segreto, con la risposta rifiutata e Ctrl-C;
  - `select` di bash come scelta di tre opzioni;
  - `[Y/n]` come conferma, con predefinito `y`;
  - `less` come pager;
  - bash interattiva come prompt, con la guardia che rifiuta `systemctl stop sshd` digitato nella shell;
  - pacman riconosciuto dal suo profilo, con l'elenco dei pacchetti: risposta no, nulla installato;
  - `sleep` fermo dopo 30 secondi.
- **Profilo scritto dall'agente.** Una sessione di Claude Code sulla Deck (`claude -p`, solo strumenti MCP) ha:
  - avviato `ssh-keygen` e risposto alla domanda del file;
  - scritto il profilo, provato con `term_profile_test` finché riconosceva le domande, e salvato;
  - alla passphrase, interrotto senza digitarla;
  - chiuso la sessione con anteprima e conferma.

  Ha anche notato il difetto della domanda vecchia che vinceva sulla nuova, corretto con la regola della riga del
  cursore.

## Limiti noti

- Un programma che aspetta la rete può dormire in `wait_woken` come uno che legge dal terminale. Se è fermo e
  il suo ultimo prompt non si riconosce, risulta `waiting_input` con domanda `unknown`.
- Nei menu a frecce (per esempio quelli di `gh auth login`) le opzioni scritte sotto la riga del cursore non
  entrano in `question.options`, perché una domanda deve finire sulla riga del cursore. Le righe restano in
  `terminal.lines` e si sceglie con `key` (frecce e Invio). Segnalato dall'agente della Deck il 26/10/2026.
- Le applicazioni a tutto schermo (editor, `htop`, menu di `dialog`) arrivano come righe dello schermo con domanda
  `unknown`: si guidano con `key`. Un profilo può riconoscerne le schermate.
- Fra le opzioni di `sudo` e degli altri involucri, solo quelle note con argomento vengono saltate per trovare
  il programma.
