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
