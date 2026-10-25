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
