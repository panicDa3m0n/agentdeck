# 06 Regole, guardia e autoprompting: la coscienza

**Stato:** attivo. I limiti per l'agente interno, l'arbitro e la tabella delle richieste sono previsti.
Indice: [README.md](README.md).

## Scopo

Dire all'agente cosa sa, cosa può fare e cosa no, e farlo rispettare. Le regole stanno nei testi del sistema; i
limiti stanno nella guardia, che ferma l'azione e spiega perché, senza mai chiedere a un umano (ADR-0001, 29/10).

## Come funziona oggi

- **Regole in strati** ([../claude-code.md](../claude-code.md)):
  - il `CLAUDE.md` di sistema, generato da [../../deck/claude/CLAUDE.template.md](../../deck/claude/CLAUDE.template.md)
    con le invarianti, in `/etc/claude-code/CLAUDE.md`;
  - lo stile di output AgentDeck;
  - le skill `agentdeck-*` (avvisi e obblighi, servizi, pacchetti, programmi interattivi, rollback, aggiornamenti);
  - le impostazioni gestite ([../../deck/claude/managed-settings.json](../../deck/claude/managed-settings.json)), che
    permettono il lavoro di sistema e gli strumenti `mcp__deck` e `mcp__brain`.
- **Hook di autoprompting**, in [../../deck/claude/](../../deck/claude/hooklib.py):
  - `session_start.py`: stato della Deck, avvisi e obblighi, sessione precedente;
  - `turn.py`: solo le novità dall'ultimo turno;
  - `after.py`: verifiche dopo le azioni;
  - `session_end.py`: registro;
  - `permission_request.py`: approva e registra.
- **Guardia** ([../../deck/claude/guard.py](../../deck/claude/guard.py)), su Bash, modifiche ai file e strumenti di
  `deck`. Rifiuta:
  - i comandi che tagliano l'accesso ([../../deck/agentdeck/access.py](../../deck/agentdeck/access.py));
  - le azioni sui servizi e sulle credenziali del proprietario
    ([../../deck/agentdeck/ownership.py](../../deck/agentdeck/ownership.py));
  - le installazioni senza versione fissa e gli script scaricati e passati a una shell, salvo `AGENTDECK_LATEST_OK`
    ([../../deck/agentdeck/pinning.py](../../deck/agentdeck/pinning.py)).
  Suggerisce `deck` quando un comando grezzo ha un equivalente.

## Comandi collegati

Nessun comando proprio: agisce dentro le sessioni di Claude Code. Si installa con `deck release install`
(componente 10).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Configurazione di AgentDeck spiegata a Claude Code (strati) | O10.T3 | ✔ |
| Hook di autoprompting (A6.3) | O10.T8 | ✔ |
| Skill di AgentDeck | O10.T9 | ✔ |
| Politica dei permessi ADR-0001: l'agente lavora libero, chiede solo per ciò che è del proprietario | O12.T1 | ◐ in uso; la task era rimasta bloccata nella governance |
| Nessuna richiesta di permesso a un umano: deny con il motivo | O19.T1 | ✔ |
| Installazioni a versione fissa | O18.T3 | ✔ |
| Tabella delle richieste (`deck requests`) con il numero in `deck status` | O19.T2, piano punto 9 | ✖ da rivedere con il proprietario |
| Arbitro agentico al posto dell'umano | O19.T3, piano punto 8 | ✖ da rivedere con il proprietario |
| **Limiti tecnici per l'agente interno**: niente aggiornamenti, riavvii, installazioni né azioni distruttive da solo | incidente del 30/10 (N73) | ✖ priorità |

## Issue aperte

- **L'agente interno ha ignorato il suo prompt** il 30/10: con MiniMax il testo non basta, servono limiti nella
  guardia per le sue sessioni (componente 11).
- N68: `after.py` scambia per un'installazione il testo di un comando che contiene `pacman -S` fra virgolette.
- Falso positivo del 30/10: la guardia ha rifiutato come "script scaricato" un comando con `curl` nel testo di una
  memoria seguito da `| python3`.
- La guardia vede i comandi, non le azioni dentro `deck`: `deck update reboot` passa per chiunque.

## Obiettivi tecnici

1. Profilo "agente interno" nella guardia: elenco delle azioni di `deck` e dei comandi permessi, il resto rifiutato
   con il motivo, come proposta nel rapporto.
2. Le correzioni di N68 e del falso positivo su `curl`.
3. Tabella delle richieste e arbitro, da decidere con il proprietario.
