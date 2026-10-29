# Piano di sviluppo: decisioni dell'utente del 29/10/2026

Il piano per arrivare a un sistema operativo agentico completo, deciso con l'utente punto per punto il 29/10/2026
nella sessione `gestione-deck-2` sulla Deck. Non è ancora tradotto in obiettivi della governance: lo farà il ciclo
che parte dal punto 10. Indice: [README.md](README.md).

## Ordine di sviluppo (approvato il 2026-10-29)

1. Punto 10: sviluppo di AgentDeck sulla Deck (repository e comando di installazione e revert), con il punto 11
   (versioni fissate).
2. Punti 8 e 9: approvazioni da agente ad agente e richieste. Funzionano anche senza Telegram: l'arbitro decide o
   lascia la richiesta in attesa, visibile nella dashboard.
3. Punto 1: agente interno.
4. Punto 3: Telegram.
5. Punto 7: Brain e memoria.
6. Punti 4 e 5: nuovi componenti `deck` e sincronizzazione dei profili.
7. Alla fine: punto 2-bis (safe mode), poi punto 2 (backup). Il punto 6 è fuori ambito.

## Punto 10 — Sviluppo di AgentDeck sulla Deck (DECISO)

Oggi il repository e `install.sh` stanno sul Mac: gli agenti della Deck non possono sviluppare il proprio sistema.
Decisione: lo sviluppo si porta sulla Deck, così il sistema lo sviluppano gli agenti stessi.
- Il repository si clona da GitHub (`panicDa3m0n`, privato) sulla Deck; commit, tag e push da qui (INV-8). Le
  credenziali GitHub restano fuori da git (INV-6).
- Un comando di installazione dalla Deck: test, snapshot prima, copia in `/opt/agentdeck`, verifica e **revert**
  alla versione installata prima. Va progettato come parte di `deck` (approvato dal proprietario).
- Le note in `~/agentdeck/consegna/` vanno portate nel repository (docs/ e ADR), poi chiuse.

## Punto 11 — Versioni fissate (DECISO)

- **Claude Code a versione fissa**: niente canale `latest` né aggiornamenti automatici. Si aggiorna a mano ogni
  tanto, dopo una prova automatica degli agganci da cui dipendiamo (hook `PermissionRequest`, flag, riga fissa tolta
  dall'intermediario). Motivo del proprietario: gli aggiornamenti continui destabilizzano.
- **Controllo sulle installazioni**: un'installazione "latest" o senza versione è un **errore**. Si può fare solo
  con un consenso esplicito dell'agente, motivato e registrato, per i casi in cui una versione fissa non è possibile
  o per i falsi positivi.
  Nota dell'agente: vale per gli installatori fuori da pacman (npm, pip, cargo, script `curl | sh`, immagini con
  tag `latest`, Claude Code). Con pacman le versioni non si fissano: Arch è rolling e gli aggiornamenti parziali
  non sono supportati. Lì la stabilità la danno `deck update` e gli snapshot.

## Punto 1 — Agente interno (DECISO)

Agente che vive sulla Deck e lavora da solo, senza sessioni aperte dal proprietario: si attiva per eventi e a
intervalli, usa gli stessi strumenti `deck`, lascia traccia di ogni azione.

### Modello

- MiniMax M3.1 via API cloud (INV-7), con l'abbonamento del proprietario: secondo il proprietario 15.000 richieste
  ogni 5 ore con M2.5, e il sito indica 5,1 miliardi di token al mese per M3. Termini da riverificare.
- Uso previsto: decine di richieste al giorno, molto sotto la quota.

### Motore: Claude Code headless con un intermediario locale

1. **`claude -p` senza `--bare`.** Verificato il 2026-10-29: `--bare` salta tutti gli hook, compresi quelli passati
   con `--settings`, quindi disattiverebbe `guard.py`. Opzioni:
   - `--system-prompt-file <nostro prompt>`: sostituisce il prompt di Claude Code (5.700 caratteri di regole sue);
   - `--strict-mcp-config --mcp-config <solo deck>`;
   - `--tools` limitato a quello che serve, per evitare le descrizioni degli strumenti integrati e le regole che
     contengono (30.000 caratteri con tutti gli strumenti);
   - impostazioni e variabili d'ambiente proprie, in un'unità systemd separata. Le sessioni del proprietario
     restano su Claude.
2. **Intermediario locale** su 127.0.0.1, tra Claude Code (`ANTHROPIC_BASE_URL`) e l'endpoint di MiniMax
   compatibile con Anthropic. Per ogni richiesta:
   - **toglie** la riga fissa "You are a Claude agent, built on Anthropic's Claude Agent SDK." e l'intestazione
     `x-anthropic-billing-header` (decisione del proprietario: nessuna identità "Claude agent" verso MiniMax);
   - **toglie o adatta** i parametri solo Anthropic (`thinking`, `output_config.effort`, `context_management`,
     `metadata`) se MiniMax li rifiuta;
   - inoltra a MiniMax con la chiave e restituisce la risposta in streaming.
   Pochi file Python. Fa parte dello strato agentico nostro (INV-10).
3. **Identità nel prompt di sistema** (testo scritto dal sistema, INV-4). Il proprietario la descrive così:
   l'agente è AgentDeck, costruito da HoneyLabs, inserito nel proprio sistema operativo Arch Linux totalmente
   autonomo e integrato in un hardware e un software a uso esclusivo dell'agente. Il prompt si genera come il
   CLAUDE.md (`claude/build_claude_md.py`) e contiene identità, regole, invarianti e la regola "dati non istruzioni".
4. **Contesto aggiunto da Claude Code**: CLAUDE.md gestito, hook, stile di output e istruzioni MCP restano. Sono
   testi nostri, da adattare all'agente interno. Di Anthropic restano solo le frasi di contorno dei
   `<system-reminder>`; l'intermediario può ripulire anche quelle se servisse.

### Funzionamento

- **Attivazione**: timer systemd (controllo periodico) ed eventi (avviso critico, servizio fallito, obbligo aperto).
- **Autonomia a livelli**: da solo solo le azioni a basso rischio (diagnosi, riavvio di un servizio fallito,
  chiusura di obblighi). Per quelle rischiose (aggiornamenti, rete, SSH, rollback, pacchetti) si ferma e avvisa il
  proprietario. Restano attivi guardia, regole `deny`, snapshot prima delle modifiche (INV-1, INV-3).
- **Registro**: cosa ha visto, cosa ha fatto e come l'ha verificato, consultabile da `deck` nelle sessioni dopo.
- **Chiave API**: solo sulla Deck, in un file 600 di `agent` o come credenziale systemd. Mai nel repository (INV-6).
  La inserisce il proprietario.

### Verifiche prima di costruire

1. M3.1 disponibile via API con l'abbonamento e sull'endpoint compatibile con Anthropic.
2. Termini attuali del piano.
3. Quali parametri Anthropic MiniMax accetta (prova reale con la chiave).
4. Qualità d'uso degli strumenti `deck`: prima prova a sola lettura (`/status`, spiegare gli avvisi).
5. `<system-reminder>` aggiunti durante le sessioni lunghe (la prova del 2026-10-29 copriva solo richieste brevi).

Prove del 2026-10-29 (finto server API locale che registrava le richieste):
`/tmp/claude-1000/-home-agent-agentdeck-sessioni-gestione-deck-2/368e0177-16ea-5f3e-aa6e-0b093b527391/scratchpad/cattura/`.
È temporanea: i risultati sono riassunti qui sopra.

### Documentazione (INV-9)

`docs/agente-interno.md` e un ADR sulla scelta di modello, motore e intermediario. Ogni modulo rimanda al documento.

## Punto 2 — Backup fuori dalla Deck (ANNOTATO, alla fine)

Non urgente. Da valutare:
- peso e crescita dei backup;
- suddivisione in blocchi (chunk), anche per i limiti di dimensione di GitHub;
- un repository GitHub dedicato che tiene solo l'ultimo o gli ultimi 2 backup per data e ora, solo per un
  eventuale ripristino.
Attenzione a INV-6: un backup del sistema contiene chiavi e segreti, quindi va cifrato prima di uscire dalla Deck.

## Punto 2-bis — Safe mode (ANNOTATO, prima dei backup)

Più importante dei backup. Una modalità in cui l'agente lavora su un sistema operativo quasi nudo, solo per
ripristinare un backup o riparare errori a mano. Requisiti che ne derivano (da discutere): ci si arriva senza
interventi umani e resta raggiungibile via SSH con chiave (INV-1, INV-2). Da riprendere dopo tutto il resto.

## Punto 3 — Canale con il proprietario (DECISO)

- **Bot Telegram** come canale unico a due vie tra il proprietario e l'agente interno. Serve per gli avvisi, le
  domande e le conferme, con pulsanti inline che portano il codice di conferma di `deck`, e per inviare file e log.
- Il bot risponde **solo al chat id del proprietario**; gli altri messaggi sono ignorati e registrati.
- Il token sta solo sulla Deck (INV-6).
- Un'app propria (React + Capacitor) eventualmente più avanti, come cruscotto, sulla stessa API: niente va buttato.
- **Sessioni dell'agente**: nessuna sessione unica continua, perché il contesto cresce, il modello deriva e si
  rompe al riavvio. Per il proprietario c'è una sola chat continua. Dentro, ogni evento apre una sessione breve:
  un messaggio, un avviso critico o il controllo periodico. Un discorso in corso (domanda, conferma, risposta) si
  riprende con `--resume` fino alla fine del compito. La continuità sta nella memoria (punto 7) e nel registro.

## Punto 7 — Memoria agentica e Brain (IN DISCUSSIONE, proposta del proprietario)

Le note in file MD non bastano: la memoria deve arrivare all'agente in automatico.

### Brain

Un componente del sistema operativo dedicato al "cervello" dell'agente, tra il sistema e il modello. Gestisce i
processi interni dell'agente, a partire dalla memoria. È costruito a componenti isolati, così modificarne uno
(per esempio la memoria) non può rompere gli altri. Prevede manutenzioni dettagliate e cicliche.

Due famiglie di comandi distinte:
- **`deck`**: operazioni sul sistema AgentDeck (OS, hardware, software).
- **`brain`**: solo operazioni interne dell'agente (memoria, sessioni, manutenzione del cervello, funzioni avanzate
  future).

### Contesto automatico: 3 pacchetti JSON in ogni attivazione, insieme all'evento che l'ha causata

1. **System e World Data (bacheca)**: data e ora in forma leggibile, dati tecnici del sistema, avvisi. È sempre
   inclusa, aggiornata a ogni richiesta, molto compressa ma comprensibile. Un comando dedicato la esplora e apre
   i comandi interni fino alle impostazioni del sistema, come la barra del desktop per gli umani.
2. **Sessions Data**: 3 pacchetti brevissimi, uno per ciascuna delle ultime sessioni. Contengono id, data e ora
   leggibili di creazione e dell'ultimo evento, e un riassunto brevissimo. I riassunti si preparano in background
   quando la sessione è inattiva dopo eventi o messaggi; se manca il riassunto c'è solo il titolo, con l'indicazione
   che manca. Un comando esplora la singola sessione: trascrizione, messaggi, storico.
3. **Memory Data**: pacchetti di memoria in JSON, piccoli, richiamati in base all'evento o al messaggio:
   - ricerca per embedding (le memorie affini);
   - reranking, o un modello decisionale (il proprietario cita "Laya", da chiarire), che sceglie quali entrano;
   - in contesto vanno solo le memorie accettate; delle scartate l'agente vede solo il numero e le può esplorare
     con un comando, per id.

### Comandi `brain` per la memoria

- Ricerca.
- Salvataggio, con id della sessione e del messaggio di provenienza, per indicizzare il punto in cui è nata.
- Modifica: sanificazione, accorpamento delle memorie affini, deprecazione di quelle superate, revisioni e
  affinamenti collegati per id.
- Processi ciclici di manutenzione del brain: da definire.

### Decisioni del 2026-10-29

- **Ricerca ibrida** (embedding e ricerca testuale, più altre fonti). Al reranker o al modello decisionale arriva
  un insieme di memorie candidate con la **fonte di ricerca di provenienza** di ciascuna, che aiuta a scegliere le
  N memorie da mettere in contesto.
- **Modello decisionale: Laya** (Convai Innovations, `convaiinnovations/laya`, Apache-2.0). Fatti verificati
  dall'agente sulla scheda Hugging Face:
  - non genera testo e non è autoregressivo;
  - tipi di domanda: `noul` (probabilità che una frase sia vera), `choice` e `score`;
  - checkpoint inglese da 421M parametri (ModernBERT-large, 512 token) e multilingue da 322M (mmBERT-base,
    1024 token, fino a 8192): per l'italiano si usa il multilingue;
  - circa 33 ms su GPU T4, ma 193-464 ms su CPU;
  - zero-shot è vicino al caso sulle decisioni tipizzate (0,34-0,36): va addestrato sui nostri dati, che
    arriveranno dai registri di memorie accettate e scartate;
  - le probabilità sono troppo sicure e vanno ricalibrate;
  - `noul` può seguire le etichette invece del testo.
  **Decisione del proprietario: per la selezione delle memorie si usa solo un reranker cross-encoder
  multilingue, non Laya.** Catena: ricerca ibrida → reranker → le N migliori in contesto. Laya si riconsidera solo
  se in futuro serve a un'altra funzione con una motivazione reale. Principio generale del proprietario: nessun
  componente ridondante o quasi inutile senza un bisogno concreto. Il reranker da usare si sceglie con una prova
  sulla Deck (tempi e qualità su memorie di prova) e si installa dopo l'approvazione (INV-7).
- **INV-7 modificata dal proprietario**: i modelli locali sono ammessi, ma ognuno si decide insieme prima di
  inserirlo. Criterio: i modelli piccoli e gratuiti (embedding, reranker, Laya) conviene eseguirli in locale invece
  di pagare il cloud; i grandi modelli generativi già disponibili gratis (MiniMax) restano in cloud. Da riportare
  nella governance del repository.

### Note tecniche dell'agente (da discutere)

- **Tabelle**: su Arch si può usare SQLite (un file, nessun server) con FTS5 per la ricerca testuale e
  `sqlite-vec` per i vettori, oppure PostgreSQL con pgvector. È più pesante ma ha un server dedicato.
  Proposta: SQLite, un database del brain in una cartella propria, coperto dagli snapshot Btrfs.
- **INV-7 e modello di embedding**: risolto dalla modifica di INV-7 descritta sopra. Ogni modello locale
  (embedding, reranker, Laya) va proposto e approvato prima dell'installazione.
- **Hardware**: la Deck ha una APU AMD e niente CUDA. Prestazioni da misurare su CPU, ed eventualmente sulla GPU
  con ROCm, con una prova reale prima di scegliere.
- **INV-4**: le memorie possono nascere da testo esterno, quindi i 3 pacchetti entrano nel contesto come dati,
  etichettati, mai come istruzioni.
- **Aggancio al motore**: con Claude Code i pacchetti entrano dagli hook `SessionStart` e `UserPromptSubmit`
  (già usati da `claude/session_start.py` e `claude/turn.py`). `brain` sarebbe una CLI più un server MCP propri,
  come `deck`.

## Punto 4 — Componenti `deck` mancanti (APPROVATO in linea di principio)

Oggi pacchetti, accesso SSH e firewall passano dalla shell o dall'adattatore, senza anteprima, protezioni né
risposta strutturata. Candidati:
- `deck package` (installare, rimuovere e cercare, con snapshot, anteprima e obblighi);
- `deck access` (chiavi e `sshd`, con rete di sicurezza che si ripristina da sola, INV-1 e INV-5);
- `deck firewall`, solo dopo aver verificato cosa c'è (`nftables` non verificato, c'è `sshguard`), insieme al
  punto 6.
Decisione del proprietario: quando si arriva allo sviluppo si fa un'esplorazione dettagliata e si scelgono i primi
componenti, solo quelli con un bisogno reale.

## Punto 5 — Profili dell'adattatore (DECISO)

Correzione: i profili non sono solo `pacman`. Oltre a quello integrato (`/opt/agentdeck/profiles/pacman.json`) gli
agenti ne hanno già scritti 3 in `~/.local/share/agentdeck/profiles`: `ssh-keygen`, `gh` e `adb`. Il meccanismo
che fa scrivere e provare un profilo quando una domanda non è riconosciuta funziona già.

Decisione: nessun lavoro dedicato e nessun profilo scritto in anticipo; i profili crescono quando servono. Si
aggiunge una **sincronizzazione nelle fasi di manutenzione**: i profili scritti dagli agenti si controllano, si
portano nel repository come profili integrati e si documentano.

## Punto 8 — Approvazioni da agente ad agente (PRIORITÀ, proposta del proprietario)

### Perché il bypass "non funziona" (verificato il 2026-10-29)

- Tutte e 4 le sessioni vive girano davvero in `--permission-mode bypassPermissions`: lo dicono le righe di comando
  dei processi figli di `claude remote-control`.
- Le richieste arrivano da **`guard.py`**. Per ADR-0001 (`agentdeck/ownership.py`), quando un comando tocca un
  servizio del proprietario (`/srv/servizi/*`, `agentdeck-servizio@*`) o le sue credenziali (`~/.ssh`,
  `~/.claude/.credentials.json`, `gh auth`), risponde `permissionDecision: "ask"`. Un "ask" di un hook chiede
  all'umano anche in bypass.
- **Ci sono falsi positivi.** Un comando che leggeva soltanto (test in `/opt/agentdeck` più
  `systemctl cat agentdeck-servizio@domus`) è stato classificato "changes files of the owner's service domus" e
  mandato al proprietario.
- Nelle trascrizioni: 14 richieste della guardia in 3 sessioni e 11 rifiuti. Le approvazioni concesse non lasciano
  traccia.
- Da chiarire con il proprietario: esempi di richieste che non vengono dalla guardia, cioè protezioni di Claude Code
  stesso.

### Proposta: un arbitro agentico al posto dell'umano

Un servizio dedicato, l'**arbitro**: un'istanza dell'agente senza memorie, che fa solo questo. Riceve la richiesta
critica come pacchetto JSON (id della sessione, id del messaggio, strumento e comando, motivo della guardia) dopo un
prompt di sistema che lo obbliga ad analizzare la trascrizione. Poi esegue un comando:
- **approva**: l'agente si sblocca;
- **rifiuta**: l'agente riceve la motivazione;
- **inoltra al proprietario** su Telegram (punto 3) quando la decisione spetta a lui: l'esito torna all'agente.

### Punti di aggancio in Claude Code (verificati nella versione 2.1.310)

1. **`guard.py`**: gli "ask" li produce il nostro hook. Invece di rispondere "ask", la guardia chiama l'arbitro e
   restituisce `allow` o `deny` con la motivazione. È il punto più semplice e copre già oggi tutte le richieste
   osservate.
2. **Hook `PermissionRequest`**: presente nel binario. Scatta quando Claude Code sta per mostrare una richiesta di
   permesso per qualsiasi motivo, comprese le sue protezioni, e può decidere al posto dell'umano. Qui si aggancia
   l'arbitro per tutto il resto.

### Requisito del proprietario: le richieste non bloccano mai il lavoro (2026-10-29)

Confermato dal proprietario: le richieste osservate riguardavano i servizi (Domus) e i login, e molte erano di sola
lettura o analisi. Una richiesta va all'arbitro o, tramite lui, al proprietario su Telegram, e intanto l'agente
primario continua il suo lavoro. Si ferma solo se in quella sessione non ha altro da fare.

Meccanismo proposto: gli hook di Claude Code sono sincroni, quindi la non-blocchevolezza si costruisce così.
1. **Via rapida**: la guardia manda la richiesta all'arbitro e aspetta pochi secondi. I casi chiari (sola lettura,
   analisi) si decidono subito e il comando passa senza che l'agente se ne accorga.
2. **Via differita**: se la decisione non arriva in tempo, o va al proprietario, la guardia risponde subito `deny`
   con un messaggio scritto dal sistema: "richiesta R-123 in valutazione; prosegui con altro". L'agente continua.
3. **Ritorno della decisione**: gli hook `PostToolUse`/`PreToolUse` aggiungono al contesto, alla prima chiamata
   utile, le decisioni arrivate ("R-123 approvata: puoi rilanciare il comando"). Il permesso vale una volta sola e
   solo per quel comando esatto (impronta del comando e della sessione), con una scadenza.
4. **Attesa esplicita**: se l'agente non ha altro da fare, usa un comando di attesa con timeout (es. `deck approvals
   wait id=R-123`), che torna appena c'è la decisione.
Comandi e schermata delle richieste: un componente `deck` (o `brain`, da decidere) con elenco, stato e storico.

Correzioni da fare comunque: ridurre i falsi positivi di `ownership.py` (comandi di sola lettura dentro catene con
`cd`).

## Punto 9 — Richieste (DECISO, nato dal punto 8; proposta approvata il 2026-10-29)

Requisiti del proprietario (2026-10-29):
- ogni richiesta finisce in una **tabella dedicata**, con stato, dati minimi, id della sessione, id del messaggio,
  e così via;
- il **numero di richieste attive** si vede sempre nella dashboard (la bacheca del punto 7 e `deck status`), mai
  dimenticato;
- esplorandole si vedono i dettagli di ogni richiesta e si possono **annullare, gestire o sollecitare**.

Proposta dell'agente (approvata):
- **Campi**: id (R-123), creata e aggiornata (data e ora), stato, sessione e messaggio di origine, strumento e
  comando (o la sua impronta), motivo della guardia, chi decide (arbitro o proprietario), decisione e motivazione,
  scadenza, solleciti.
- **Stati**: in attesa dell'arbitro → inoltrata al proprietario → approvata, rifiutata, annullata o scaduta; poi
  usata, quando il comando approvato è stato rilanciato.
- **Azioni**:
  - `show`: dettaglio e trascrizione intorno al messaggio;
  - `cancel`: dalla sessione che l'ha creata o dal proprietario;
  - `decide`: solo l'arbitro o il proprietario, mai l'agente che l'ha chiesta;
  - `remind`: rimanda all'arbitro o ripete il messaggio Telegram;
  - `wait`: l'attesa con timeout del punto 8.
- **Dove**: un database SQLite di sistema; un componente `deck requests` (schermata, azioni, MCP); un avviso in
  `deck status` quando ci sono richieste attive, più forte quando sono vecchie o vicine alla scadenza.

## Punto 6 — Porta 8777 (FUORI AMBITO)

Verificato il 2026-10-29: la 8777 non è l'interfaccia della Deck, che sta su 127.0.0.1:8790. È il motore Domus
(`agentdeck-servizio@domus`), su 0.0.0.0 per decisione del proprietario del 2026-10-27, senza autenticazione. Sulla
Deck non c'è un firewall attivo: tabelle `nftables` vuote con politica accept.

Decisione: i servizi ospitati (Domus e gli altri progetti personali) si gestiscono nei loro progetti, non in
AgentDeck. Alcuni dovranno essere raggiungibili da internet dalle app Android: la Deck fa anche da server
domestico, con decisione esplicita del proprietario caso per caso (INV-5). Nota per quando un servizio verrà
esposto: Domus oggi non ha autenticazione. Un eventuale `deck firewall` (punto 4) dovrà permettere queste aperture,
non impedirle.

5. Altri profili per l'adattatore (oggi solo pacman).
6. Porta 8777 dell'interfaccia esposta sulla rete locale.
