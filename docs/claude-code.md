# Claude Code sulla Deck

Claude Code è l'harness degli agenti di AgentDeck (decisione D1, [architettura.md](architettura.md), sezioni
6, 7.4 bis e 7.5): non modificato, perché la licenza non lo permette, e integrato con le estensioni previste da
Anthropic. Questo documento descrive come è installato sulla Deck e come si verifica.

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
| 3. Vincoli duri | `/etc/claude-code/managed-settings.json` | [../deck/claude/managed-settings.json](../deck/claude/managed-settings.json) | Regole `deny` gestite, che nessun livello scavalca, sugli stop e disable dei servizi di accesso; modalità che salta i permessi disattivata; i due hook qui sotto |
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
- le impostazioni gestite li permettono tutti (`permissions.allow: ["mcp__deck"]`), senza chiedere a una persona.
  Le azioni distruttive restano protette da `deck` stesso: prima l'anteprima, poi il codice di conferma;
- `CLAUDE.md` indica gli strumenti MCP come via principale e la riga di comando `deck` come alternativa;
- i programmi interattivi passano dall'adattatore, gli strumenti `mcp__deck__term_*` ([adattatore.md](adattatore.md)):
  la sessione legge le loro domande come dati, non digita segreti e scrive i profili dei programmi nuovi.

Claude Code carica gli strumenti MCP solo quando servono: la sessione li trova con la ricerca degli strumenti, e
così si è comportata nella prova del 26/10/2026 (`open /status`, poi l'anteprima di `snapshot_rollback` senza
conferma).

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
