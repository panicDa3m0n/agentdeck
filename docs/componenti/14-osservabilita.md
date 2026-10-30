# 14 Osservabilità ed eventi: i sensi

**Stato:** parziale. Avvisi e log sono attivi; eventi, registro delle azioni e storia degli avvisi sono previsti.
Indice: [README.md](README.md).

## Scopo

Sapere cosa succede sulla Deck e cosa ha fatto l'agente, in forma di dati: avvisi con un codice, eventi, log
strutturati, una traccia delle azioni.

## Come funziona oggi

- **Avvisi di `deck status`** con codice stabile (per esempio `TIME_NOT_SYNCED`, `FAN_UNREADABLE`) e l'azione che li
  gestisce. Gli hook li portano a inizio sessione e a ogni turno, solo le novità (componente 06).
- **`deck logs query`:** il journal per unità, periodo e gravità, come dati; la traccia dei comandi dell'agente è
  esclusa salvo `include_agent=true`.
- **Righe dello schermo:** ogni chiamata a `deck` e `brain` scrive `indirizzo|azione|stato|codice|avvisi` nel journal
  (`agentdeck`). Il 30/10 sono servite a ricostruire le azioni dell'agente interno.
- **Registri di AgentDeck** in `~/.local/state/agentdeck/`: corse e tick dell'agente interno, intermediario,
  richieste al proprietario, sessioni di Claude Code (`session_end.py`).

## Comandi collegati

`deck status`, `deck logs query`, `deck obligations`.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Stato del sistema con avvisi | O3.T1 | ✔ |
| Log strutturati per servizio, periodo e gravità | O5.T2 | ✔ |
| Studio di eventi, log e osservabilità | O8.T5 | ✔ in [../architettura.md](../architettura.md), sezione 5 |
| Traccia dei comandi dell'agente fuori dal journal di sistema | A5.1 | ✖ |
| `OnFailure=` globale: ogni servizio che fallisce è un evento | A5.2 | ✖ |
| Raccoglitore di eventi `agentdeck-events` | A5.3 | ✖ |
| Briefing di inizio sessione `deck inbox` | A5.4 | ◐ in parte con gli hook di inizio sessione e di turno |
| Risveglio dell'agente per evento | A5.5, D7 | ◐ con `deck agent tick` (sospeso, componente 11) |
| Registro strutturato delle azioni dell'agente | A5.6 | ✖ (oggi solo le righe dello schermo) |
| Avvisi con una storia (prima e ultima comparsa, risoluzione) | A5.7 | ✖ |
| Tasto di accensione come evento | A5.8 | ✖ |
| `systemd-oomd` con limiti per i lavori dell'agente | A5.9 | ✖ |
| `auditd` con regole sull'agente | A3.8 | ✖ (componente 15) |

## Issue aperte

- Ricostruire chi ha fatto cosa richiede di incrociare il journal (`sudo`, righe `agentdeck`) e i registri: il
  30/10 l'azione dell'agente interno si è vista così, ma nessun registro la attribuiva.
- La corsa interrotta da un riavvio non lascia traccia (componente 11).

## Obiettivi tecnici

1. A5.6, registro delle azioni con sessione e agente: è la base anche per il Brain (riassunti) e per l'arbitro.
2. A5.2 e A5.7, piccoli e molto utili.
