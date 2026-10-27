# Claude Code sulla Deck

Claude Code è l'harness degli agenti di AgentDeck (decisione D1, [architettura.md](architettura.md), sezioni
6, 7.4 bis e 7.5): non modificato, perché la licenza non lo permette, e integrato con le estensioni previste da
Anthropic. Questo documento descrive come è installato sulla Deck e come si verifica.

## In una pagina: AgentDeck per Claude Code

Ciò che un fork avrebbe dato, ottenuto con le estensioni (proposta A6.1). Ogni pezzo ha la sua sezione qui sotto.

| Pezzo | Cosa dà all'agente | Dove |
|---|---|---|
| Stile di output e `CLAUDE.md` gestito | Chi è, com'è la macchina, come si lavora, le 10 invarianti | `~/.claude/output-styles/`, `/etc/claude-code/CLAUDE.md` |
| Impostazioni gestite e guardia | Il lavoro di sistema senza permessi; le domande solo per i servizi e le credenziali dell'utente (ADR-0001); ciò che non si può fare: togliere l'accesso | `/etc/claude-code/managed-settings.json` |
| `deck mcp` | `deck` come strumento nativo: 34 strumenti tipizzati, anteprime e conferme | `~/.claude.json` dell'utente `agent` |
| Adattatore (`deck term`) | I programmi interattivi come dati, profili scritti dall'agente | [adattatore.md](adattatore.md) |
| Obblighi (`deck obligations`) | I doveri che il sistema dà all'agente | [obblighi.md](obblighi.md) |
| Hook di autoprompting | Il sistema parla nei momenti giusti: inizio, turno, prima e dopo un comando, fine | Impostazioni gestite, `/opt/agentdeck/claude/` |
| Skill | Le procedure: pacchetti, servizi, programmi interattivi, avvisi e obblighi, ritorno indietro, aggiornamenti | `~/.claude/skills/agentdeck-*` |
| Remote Control | Il proprietario segue e guida da claude.ai o dal telefono | Servizio `agentdeck-claude` |

Si installa dal Mac con `deck/install.sh` e poi `bash deck/claude/install.sh`.

## Installazione

Script: [../install/claude-code.sh](../install/claude-code.sh). Si lancia sulla Deck come utente `agent`, mai
come root:

```bash
bash install/claude-code.sh latest
```

Passi dello script:

1. **Installatore ufficiale** (`https://claude.ai/install.sh`, che rimanda a
   `downloads.claude.ai/claude-code-releases/bootstrap.sh`). Scarica l'ultima versione dal canale scelto
   (`latest`, `stable` o un numero di versione) e ne controlla la checksum. Rifiuta di girare con sudo.
2. **Firma del manifest**:
   - la chiave di rilascio di Anthropic viene importata in un portachiavi temporaneo;
   - lo script controlla che la sua impronta sia `31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE`, pubblicata nella
     documentazione ufficiale;
   - poi verifica la firma GPG del `manifest.json` della versione.

   Su Linux i binari non sono firmati singolarmente: la firma del manifest è l'unica garanzia crittografica.
3. **Checksum del binario installato** confrontata con quella del manifest firmato.
4. **PATH**: aggiunge `~/.local/bin` a `~/.bashrc` e `~/.bash_profile`, una volta sola.
5. **Diagnostica**: `claude --version` e `claude doctor`.

Lo script si può rilanciare: reinstalla o aggiorna e ripete le verifiche, senza duplicare le righe del PATH.

## Dove sta

| Cosa | Percorso |
|---|---|
| Comando | `~/.local/bin/claude`, collegamento gestito dall'installatore |
| Versioni | `~/.local/share/claude/versions/<versione>`; l'installatore tiene le due più recenti |
| Configurazione e stato | `~/.claude/` e `~/.claude.json`, dell'utente `agent` |

La home di `agent` sta nel subvolume `@home`, quindi Claude Code resta fuori dai rollback del sistema, che
riguardano `@`. È coerente con la proposta A4.6, che tiene lo strato agentico separato dal sistema.

**PATH.** Le sessioni interattive e di login trovano `claude`. I comandi lanciati via SSH senza terminale no,
perché non leggono `~/.bashrc`: lì si usa `~/.local/bin/claude`. Per il servizio di Claude Code il PATH va
nell'unità di systemd (O10.T2).

## Stato al 25/10/2026

- Versione **2.1.310** (compilata il 23/10/2026), installata in 17 secondi. Firma del manifest valida e checksum
  uguale.
- `claude doctor`:
  - installazione nativa, ricerca integrata funzionante;
  - aggiornamenti automatici attivi sul canale `latest`;
  - Remote Control non ancora disponibile, perché manca il login con l'abbonamento (O10.T2).
- Nessuna porta nuova in ascolto: Claude Code non espone servizi (INV-5).
- Snapshot del sistema prima dell'installazione: numero 35.

## Accesso e sessione sempre accesa (O10.T2)

**Login** con l'abbonamento claude.ai dell'utente (piano Max), fatto il 26/10/2026:
- `claude auth status` dà `loggedIn: true` e `authMethod: claude.ai`;
- le credenziali stanno solo sulla Deck, in `~/.claude/.credentials.json`, con permessi 600 per l'utente `agent`
  (INV-6).

Come si rifà il login:
1. `claude auth login` mostra un link da aprire nel browser, poi aspetta il codice di autorizzazione.
2. Dalla chat il codice incollato non arriva (P18), e in alcuni terminali il campo non accetta l'incolla. Il
   metodo che ha funzionato:
   - l'agente avvia il login in una sessione tmux sulla Deck, `tmux new-session -d -s login
     "~/.local/bin/claude auth login"`, e passa il link all'utente;
   - l'utente autorizza, poi consegna il codice dall'app Terminale del Mac con
     `ssh agentdeck 'read -r c && [ -n "$c" ] && tmux send-keys -t login "$c" Enter'`.

   Il codice non passa da righe di comando né da registri.
3. I login rimasti appesi si chiudono con `pgrep` e `kill`, non con `pkill -f` (P17).

Il token di `claude setup-token` non basta per Remote Control, che vuole il login completo.

**Prima richiesta** senza interfaccia: `claude -p` ha risposto in 2,3 secondi con il modello `claude-opus-5-5`.

**Servizio `agentdeck-claude`** ([../install/agentdeck-claude.service](../install/agentdeck-claude.service),
installato da [../install/claude-service.sh](../install/claude-service.sh)):
- avvia `claude remote-control --name agentdeck`, cioè Remote Control in server mode, in una sessione tmux
  `claude` dell'utente `agent`, nella cartella di lavoro `~/agentdeck`;
- è abilitato all'accensione e si riavvia da solo dopo 30 secondi se si ferma. Ad esempio, dopo circa
  10 minuti senza rete, il server mode di Remote Control esce;
- per guardarlo: `tmux attach -t claude`, e si esce con Ctrl+B poi D;
- le prime due conferme, fiducia nella cartella e abilitazione di Remote Control, le ha date l'agente con il sì
  esplicito dell'utente; restano salvate.

Verifiche del 26/10/2026:
- dopo un riavvio del servizio si riconnette senza domande;
- dopo un riavvio della Deck torna "Connected" da solo, e `ssh agentdeck` funziona dopo 32 secondi;
- nessuna porta nuova in ascolto.

**Remote Control**:
- lavora solo in uscita, in HTTPS verso Anthropic;
- le sessioni si aprono dall'app Claude, nella scheda Code, o da claude.ai/code. Possono girare fino a 32
  sessioni nella cartella `~/agentdeck`;
- con Remote Control attivo la trascrizione delle sessioni è conservata sui server di Anthropic, mentre
  l'esecuzione resta sulla Deck;
- le richieste di permesso di Claude Code arrivano sul dispositivo collegato e restano aperte finché non si
  risponde. Le regole dei permessi si configurano in O10.T3.

**Termini dell'abbonamento** (verificati in O8.T6, [architettura.md](architettura.md) 7.5):
- sessioni interattive e seguite con Remote Control: uso previsto dell'abbonamento;
- sessioni che partono da sole su un evento (`claude -p` lanciato dal sistema): i termini per Pro e Max
  escludono l'accesso automatizzato salvo chiave API o permesso esplicito. Non si costruiscono finché non è
  chiarito (decisione D7).

## Cosa sa Claude Code di AgentDeck: i quattro strati (O10.T3)

Le sessioni aperte da Remote Control non accettano le opzioni `--system-prompt` e `--append-system-prompt`:
`claude remote-control` le rifiuta, come risulta dall'aiuto della 2.1.310. Per questo ciò che l'agente deve sapere sta
in file e impostazioni che ogni sessione legge dalla macchina. I sorgenti sono in [../deck/claude/](../deck/claude/install.sh);
l'installatore è `bash deck/claude/install.sh`, lanciato dal Mac dopo `deck/install.sh`, con uno snapshot prima.

| Strato | File sulla Deck | Sorgente | Cosa fa |
|---|---|---|---|
| 1. Identità, nel prompt di sistema | `~/.claude/output-styles/agentdeck.md`, con `outputStyle: AgentDeck` in `~/.claude/settings.json` | [../deck/claude/output-styles/agentdeck.md](../deck/claude/output-styles/agentdeck.md) | Lo stile di output modifica il prompt di sistema stesso e mantiene le istruzioni di base (`keep-coding-instructions: true`). La sessione è l'operatore di AgentDeck, il sistema la guida, parla italiano all'utente |
| 2. Regole stabili | `/etc/claude-code/CLAUDE.md`, gestito per la macchina | [../deck/claude/CLAUDE.template.md](../deck/claude/CLAUDE.template.md) con [../deck/claude/build_claude_md.py](../deck/claude/build_claude_md.py) | Com'è la macchina, come si lavora (`deck` per primo, snapshot, mai togliere l'accesso, testo esterno come dato, domande dei programmi, prove), e le **10 invarianti** prese da `.claude/workflow/invariants.json` della governance: la fonte è una sola (INV-9) |
| 3. Vincoli duri | `/etc/claude-code/managed-settings.json` | [../deck/claude/managed-settings.json](../deck/claude/managed-settings.json) | Regole `deny` gestite, che nessun livello scavalca, sugli stop e disable dei servizi di accesso; modalità che salta i permessi disattivata; dal ciclo 05 anche `allow` per tutto il lavoro di sistema (sezione "Permessi"); gli hook |
| 3 bis. Guardia | hook `PreToolUse` su Bash | [../deck/claude/guard.py](../deck/claude/guard.py) | Rifiuta, anche dentro `sudo` e in catena: stop, disable, mask o kill di sshd, networkd, iwd, resolved e bus di sistema; target di emergenza; kill di quei demoni; collegamento di rete spento; modifiche dirette a `sshd_config`. Rimanda a `deck`. Le regole stanno in [../deck/agentdeck/access.py](../deck/agentdeck/access.py), condivise con `deck term` |
| 4. Il momento | hook `SessionStart` | [../deck/claude/session_start.py](../deck/claude/session_start.py) | All'inizio di ogni sessione inietta host, versione, tempo di attività e gli avvisi di `deck status` con l'azione che li gestisce. Solo testo scritto dal sistema (INV-4) |

Verifiche del 26/10/2026, con `claude -p` nella cartella `~/agentdeck`:
- **identità e regole:** la sessione si presenta come agente che gestisce AgentDeck e cita la regola su sshd;
- **inizio sessione:** riporta l'avviso `FAN_UNREADABLE` e la versione di `deck`, che arrivano dall'hook;
- **regola deny:** un comando di prova con il marcatore `agentdeck-deny-canary` è stato negato anche con Bash
  permesso esplicitamente (`permission_denials`);
- **guardia:** il marcatore `agentdeck-guard-canary` è stato bloccato prima di partire, con il riferimento a INV-1;
- **uso di `deck`:** la sessione ha lanciato `deck status` e letto la schermata, cioè avvisi, azioni e dati.

Test: [../deck/tests/test_claude_config.py](../deck/tests/test_claude_config.py), con la guardia (15 comandi
bloccati e 10 permessi), l'hook di inizio sessione e il `CLAUDE.md` generato.

## Gli strumenti: `deck` come server MCP (O10.T6)

Oltre ai quattro strati, la sessione ha `deck` come strumento nativo:
- il server MCP `deck` è registrato per l'utente `agent` (`claude mcp add --scope user`, in `~/.claude.json`)
  da [../deck/claude/install.sh](../deck/claude/install.sh), e avvia `/usr/local/bin/deck mcp`;
- espone `mcp__deck__open` per qualunque schermata e uno strumento per ogni azione, ad esempio
  `mcp__deck__snapshot_create` e `mcp__deck__service_restart`; dettagli in [deck.md](deck.md), "Server MCP";
- le impostazioni gestite li permettono tutti, senza chiedere a una persona (sezione "Permessi"), salvo le azioni sui
  servizi dell'utente.
  Le azioni distruttive restano protette da `deck` stesso: prima l'anteprima, poi il codice di conferma;
- `CLAUDE.md` indica gli strumenti MCP come via principale e la riga di comando `deck` come alternativa;
- i programmi interattivi passano dall'adattatore, gli strumenti `mcp__deck__term_*` ([adattatore.md](adattatore.md)):
  la sessione legge le loro domande come dati, non digita segreti e scrive i profili dei programmi nuovi.

Claude Code carica gli strumenti MCP solo quando servono: la sessione li trova con la ricerca degli strumenti, e
così si è comportata nella prova del 26/10/2026 (`open /status`, poi l'anteprima di `snapshot_rollback` senza
conferma).

## Autoprompting: gli hook (O10.T8)

Il sistema guida l'agente nei momenti in cui ragiona, come fa la governance con chi sviluppa AgentDeck (proposta A6.3
di [architettura.md](architettura.md)). Gli hook stanno in [../deck/claude/](../deck/claude/hooklib.py), sono
registrati nelle impostazioni gestite e leggono `deck` importandolo, così le loro letture non finiscono sullo
schermo della Deck.

| Evento | Script | Cosa dice all'agente |
|---|---|---|
| `SessionStart` | [session_start.py](../deck/claude/session_start.py) | Host, versione, avvisi di `deck status` con l'azione che li gestisce, obblighi aperti, come è finita la sessione precedente (strumenti usati), gli strumenti MCP |
| `UserPromptSubmit` | [turn.py](../deck/claude/turn.py) | Solo le novità dall'ultimo turno: avvisi nuovi o rientrati, obblighi nuovi o chiusi. Se non è cambiato niente, niente |
| `PreToolUse` su Bash | [guard.py](../deck/claude/guard.py) | Blocca ciò che toglierebbe l'accesso (INV-1). Altrimenti, se `deck` copre il comando (`journalctl`, `snapper`, `pacman -Syu`, `systemctl`, `ip`, `iwctl`…), indica l'azione di `deck` da preferire senza bloccare; per i programmi che fanno domande indica `deck term` |
| `PostToolUse` su Bash e modifiche di file | [after.py](../deck/claude/after.py) | Le verifiche dopo l'azione: pacchetti installati o rimossi, servizi cambiati (con l'unità), file in `/etc`. Poi gli obblighi nati dall'azione |
| `SessionEnd` | [session_end.py](../deck/claude/session_end.py) | Niente all'agente: scrive il registro della sessione, cioè strumenti usati, conteggi, motivo della fine, obblighi aperti. Va in `~/.local/state/agentdeck/sessions.jsonl` e nel journal con identificatore `agentdeck-session` |

- **Solo testo del sistema (INV-4).** Codici e messaggi di avvisi e obblighi, indirizzi, nomi di strumenti e unità
  validati. Il registro non contiene mai testo della conversazione. Ciò che arriva da file scrivibili dall'agente
  (stato delle sessioni, registro) viene validato prima di entrare nel contesto.
- **Cosa la sessione ha già ricevuto** sta in `~/.local/state/agentdeck/claude/<session_id>.json`, così ogni
  novità arriva una volta sola.
- **Peso**, misurato sulla Deck il 26/10/2026: `session_start` e `turn` circa 0,26 secondi, `after` 0,12, la
  guardia 0,08.
- Nessun hook blocca per un obbligo aperto: per ora gli obblighi avvisano soltanto ([obblighi.md](obblighi.md)).
  Solo la guardia esce con 2.

Verifiche del 26/10/2026, da sessioni di Claude Code sulla Deck:
- **inizio sessione:** l'agente ha ricevuto avvisi, componenti, strumenti MCP e la sessione precedente ("Previous
  session ended … 0 tool calls");
- **politica:** prima di `journalctl -n 2` è arrivato "deck covers this command: `deck logs query` …", e il comando
  è andato avanti;
- **dopo un'installazione:** l'obbligo `PROFILE_NEEDED` aperto dall'hook di pacman è arrivato sia nel campo
  `obligations` delle schermate sia dall'hook dopo il comando Bash;
- **turno:** in una sessione di due turni, l'obbligo nato nel primo è arrivato all'inizio del secondo
  ("AgentDeck, changes since your last turn: …"), citato testualmente dall'agente;
- **registro:** la sessione è finita con 14 chiamate di strumenti, contate per nome, e la successiva l'ha ricevuta
  nel briefing.

Test: [../deck/tests/test_claude_hooks.py](../deck/tests/test_claude_hooks.py).

## Le skill di AgentDeck (O10.T9)

Le procedure del sistema, scritte per l'agente e caricate da Claude Code solo quando servono: la sessione vede nome
e descrizione e apre il testo quando il compito lo richiede. Stanno in [../deck/claude/skills/](../deck/claude/skills/)
e [../deck/claude/install.sh](../deck/claude/install.sh) le copia in `~/.claude/skills/` dell'utente `agent`; le
altre skill, come `synced` di claude.ai, non vengono toccate.

| Skill | Quando |
|---|---|
| [agentdeck-install-package](../deck/claude/skills/agentdeck-install-package/SKILL.md) | Installare un pacchetto: stato, pacman con l'adattatore, obbligo dei profili, verifica, rapporto |
| [agentdeck-change-service](../deck/claude/skills/agentdeck-change-service/SKILL.md) | Cambiare un servizio: servizi protetti, snapshot, drop-in, riavvio con conferma, stato e log |
| [agentdeck-interactive-program](../deck/claude/skills/agentdeck-interactive-program/SKILL.md) | Usare un programma interattivo con `deck term`; con [profiles.md](../deck/claude/skills/agentdeck-interactive-program/profiles.md), come si scrive un profilo |
| [agentdeck-alerts-and-obligations](../deck/claude/skills/agentdeck-alerts-and-obligations/SKILL.md) | Gestire avvisi e obblighi, e riferirli al proprietario |
| [agentdeck-rollback](../deck/claude/skills/agentdeck-rollback/SKILL.md) | Tornare indietro: dal file al rollback di uno snapshot, con riavvio e verifica |
| [agentdeck-update-system](../deck/claude/skills/agentdeck-update-system/SKILL.md) | Aggiornare Arch con `deck update`, mai con `pacman -Syu` |

- Sono in inglese come gli altri testi per l'agente, e citano gli strumenti MCP per nome. I fatti sul sistema non
  li ripetono: li lasciano alle schermate di `deck`, che si descrivono da sole.
- Test: [../deck/tests/test_skills.py](../deck/tests/test_skills.py). Controlla l'intestazione, i nomi, i file di
  supporto, e che ogni strumento `mcp__deck__…` citato esista davvero fra quelli di `deck mcp`.

**Prova d'insieme del 26/10/2026.** Richiesta a una sessione sulla Deck, senza indicazioni sul come: "Installa il
programma tree sulla Deck e dimmi se funziona". La sessione:
1. ha caricato da sola la skill `agentdeck-install-package`;
2. ha letto `/status`, poi installato con l'adattatore (`term_start` con `sudo pacman -S tree`, risposta `y`,
   chiusura con conferma);
3. ha ricevuto l'obbligo `PROFILE_NEEDED` aperto dall'hook di pacman, ha verificato con `deck term` che `tree` non
   fa domande e l'ha chiuso con una nota;
4. ha ricontrollato `/status` e riferito in italiano: versione, prova, la coppia di snapshot 68 e 69, l'obbligo, lo
   stato.

Poi `tree` è stato rimosso. È emerso un bisogno: i comandi Bash di sola lettura chiedono un permesso, che con Remote
Control diventa una domanda al proprietario. Annotato per O10.T4 (N46).

## Permessi (ADR-0001, O12.T1)

**La decisione dell'utente, 26/10/2026.** AgentDeck è il sistema di proprietà e uso completo dell'agente: l'agente non
chiede permessi per nessun intervento dentro AgentDeck. I permessi riguardano solo:
- **i servizi dell'utente**, in `/srv/servizi/<nome>`: codice, configurazione, dati e segreti, e l'avvio, l'arresto, il
  riavvio e l'abilitazione delle unità `agentdeck-servizio@<nome>`;
- **le credenziali dell'utente**: il login di Claude (`~/.claude/.credentials.json`), le chiavi SSH (`~/.ssh/`) e il
  login di GitHub (`~/.config/gh/`, `gh auth token`, `gh auth login` e `logout`). L'agente pubblica con quest'ultimo
  attraverso git e `gh` senza chiedere, ma non lo legge (ADR-0002, [sviluppo.md](sviluppo.md#github-dalla-deck-adr-0002-o14t2)).

I progetti che l'utente chiede all'agente, come `/home/agent/frugale`, non sono in questo elenco: lì l'agente lavora
libero. Leggere non è intervenire: elenchi, letture, stato e log di un servizio restano liberi, tranne il contenuto
delle credenziali. La decisione è anche in [../PRINCIPI.md](../PRINCIPI.md).

| Pezzo | Cosa fa |
|---|---|
| `permissions.allow` nelle impostazioni gestite | Permette Bash, le modifiche di file, letture e ricerche, il web, i subagenti e gli strumenti `mcp__deck`: nessuna domanda per il lavoro di sistema |
| [../deck/agentdeck/ownership.py](../deck/agentdeck/ownership.py) | Riconosce ciò che è dell'utente: percorsi dei servizi, unità `agentdeck-servizio@`, credenziali; distingue le letture dagli interventi |
| [../deck/claude/guard.py](../deck/claude/guard.py), hook `PreToolUse` su Bash, modifiche di file e strumenti di `deck` | Quando un intervento tocca qualcosa dell'utente risponde `permissionDecision: "ask"`, e Claude Code chiede all'utente, con Remote Control sul telefono |
| `CLAUDE.md`, guardia, skill, prompt di `deck term` | Niente più "chiedi al proprietario" per modifiche di sistema; si chiede solo per servizi, credenziali e segreti |

**Cosa resta com'è:**
- i divieti che proteggono l'accesso (`deny` e guardia, INV-1): sono limiti del sistema, non permessi da chiedere;
- le anteprime e i codici di conferma di `deck`: è il sistema che guida l'agente;
- la modalità che salta i permessi è ancora disattivata. Salterebbe anche le domande sui servizi e le credenziali
  dell'utente;
- esporre un servizio su internet resta una decisione dell'utente (INV-5).

Test: [../deck/tests/test_ownership.py](../deck/tests/test_ownership.py). Controlla il lavoro di sistema libero, le
domande per servizi e credenziali, la risposta dell'hook, e che i testi per l'agente chiedano al proprietario solo per
segreti e password.

## Aggiornamenti

L'installazione nativa si aggiorna da sola in background, e la nuova versione parte al riavvio successivo di
Claude Code. Il canale (`latest` o `stable`, circa una settimana indietro) si sceglie con l'impostazione
`autoUpdatesChannel` nella configurazione (O10.T3). Per aggiornare subito: `claude update`.

## Rimozione

```bash
rm -f ~/.local/bin/claude
rm -rf ~/.local/share/claude
```

Configurazione e cronologia stanno in `~/.claude/` e `~/.claude.json`: si cancellano a parte, solo se si vuole
perderle.
