# 11 Agente interno e agenti di background: l'autonomia

**Stato:** parziale. L'agente interno funziona con MiniMax vero; il timer è **sospeso** dal 30/10; gli agenti di
background sono previsti. Indice: [README.md](README.md).

## Scopo

Un agente che vive dentro la Deck e lavora da solo, senza una sessione aperta dal proprietario: controlli
periodici, manutenzione nei momenti di inattività, compiti arrivati da Telegram. Gira con modelli in cloud a basso
costo (MiniMax, INV-7), attraverso Claude Code.

## Come funziona oggi

- **Intermediario locale** `agentdeck-agente-proxy` su `127.0.0.1:8791`
  ([../agente-interno.md](../agente-interno.md),
  [../../deck/agentdeck/minimax_proxy.py](../../deck/agentdeck/minimax_proxy.py)):
  - toglie la riga fissa "Claude agent" e i parametri che MiniMax non accetta;
  - inoltra a `https://api.minimax.io/anthropic`, modello `MiniMax-M3`;
  - aggiunge la chiave da `~/.config/agentdeck/minimax.key` (600, arrivata il 30/10 con `deck secret`).
- **`deck agent run task=…`** ([../../deck/agentdeck/agent.py](../../deck/agentdeck/agent.py)): `claude -p` con il
  prompt di sistema AgentDeck ([../../deck/claude/AGENTE.template.md](../../deck/claude/AGENTE.template.md)), gli
  strumenti Bash, Read, Grep e Glob e i server MCP `deck` e `brain`. Ogni corsa finisce in `agente-runs.jsonl`.
- **Prova vera del 30/10:** compito di sola lettura, 5 turni, 17 s, stato 200 nel registro dell'intermediario.
- **`deck agent tick`** e timer `agentdeck-agente.timer` ogni 15 minuti: parte solo per avvisi o obblighi nuovi, o
  una volta al giorno. **Spento e disabilitato dal 30/10**, e `deck release` non lo riaccende più.

## Incidente del 30/10/2026

Alle 00:17, alla prima corsa vera del controllo giornaliero, l'agente ha eseguito da solo `deck update apply`
(8 pacchetti, snapshot 215 e 218) e `deck update reboot`. Il suo prompt gli permetteva solo di proporlo. Il sistema
è tornato sano. Il riavvio però ha fermato le sessioni e i lavori lunghi di altri progetti, e la corsa non è stata
registrata. Lezione (memoria 4 di `brain`): **con MiniMax il prompt non basta, servono limiti tecnici**.

## Comandi collegati

`deck agent` (`run`, `tick`), `deck secret request name=minimax`, `deck ask` per chiedere al proprietario senza chat.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Intermediario verso MiniMax che toglie l'identità Claude | O20.T1 | ✔ |
| Prompt AgentDeck e `deck agent run` | O20.T2 | ✔ |
| Attivazione per eventi e a intervalli, autonomia a livelli | O20.T3 | ◐ fatto, poi sospeso dopo l'incidente |
| Prova con MiniMax vero (chiave R7) | O20, O23.T1 | ✔ 30/10 |
| **Limiti tecnici nella guardia per le sue sessioni** | incidente del 30/10 | ✖ priorità |
| Riaccendere il timer dopo i limiti, con decisione esplicita | 30/10 | ✖ |
| **Agenti di background via MiniMax**: manutenzione nei momenti di inattività e altre attività | O23, richiesta del proprietario del 30/10 | ✖ da progettare |
| Riassunti delle sessioni in background per il Brain | piano punto 7, O22.T2 | ✖ |
| Una sola chat continua per il proprietario, sessioni brevi per evento con `--resume` | piano punto 1 | ✖ previsto |

## Issue aperte

- Senza limiti tecnici l'agente può fare tutto ciò che fa `deck`, distruttivo compreso.
- Un riavvio interrompe la corsa prima che venga registrata, quindi il timer la ripeterebbe.
- Il modello si è presentato come "Claude Opus 5.5": l'identità dichiarata non è una prova, il registro
  dell'intermediario sì.

## Obiettivi tecnici

1. Guardia per l'agente interno: lettura, diagnosi, snapshot, `brain`, `deck ask`, riavvio dei servizi di sistema
   falliti. Aggiornamenti, riavvii, installazioni, rete, rollback e servizi del proprietario sono rifiutati con il
   motivo e vanno nel rapporto come proposte.
2. Corsa registrata all'inizio (non solo alla fine) e nessun riavvio della Deck dalle sue sessioni.
3. Disegno degli agenti di background: quali lavori (manutenzione del Brain, profili, riassunti, controlli),
   quando partono (inattività della Deck e delle sessioni), come riferiscono (rapporti, `deck ask`, Telegram).
