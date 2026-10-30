# 07 Harness: Claude Code e sessioni. Il corpo dell'agente

**Stato:** attivo. Indice: [README.md](README.md).

## Scopo

Dove vive l'agente che gestisce la Deck: Claude Code non modificato, con il plugin di AgentDeck (decisione D1 del
25/10: niente API di Claude, niente fork), in sessioni che il proprietario segue con Remote Control.

## Come funziona oggi

- **Claude Code** binario nativo per l'utente `agent`, a **versione fissa** (2.1.310; disponibile la 2.1.312). Si
  aggiorna solo con `deck claude/version switch`, dopo la prova degli agganci (`probe`)
  ([../claude-code.md](../claude-code.md), [../../deck/agentdeck/claude_version.py](../../deck/agentdeck/claude_version.py)).
- **Sessioni:**
  - `agentdeck-claude`: la sessione sempre accesa;
  - `agentdeck-sessione@<nome>`: le sessioni con nome, ognuna con la sua cartella in `~/agentdeck/sessioni/`.
    Il 30/10 ce n'erano cinque, fra cui `gestione-deck-3` e quelle del progetto `frugale`.
  Tutte sono raggiungibili con Remote Control da claude.ai e dal telefono, e girano in `bypassPermissions`
  (decisione del 28/10).
- **`deck claude`:** elenca, apre (con Remote Control) e chiude le sessioni, guardando i processi veri
  ([../../deck/agentdeck/claude_sessions.py](../../deck/agentdeck/claude_sessions.py)).
- **Server MCP registrati per l'utente:** `deck` e `brain`.

## Comandi collegati

`deck claude` (`open`, `close`), `deck claude/version` (`probe`, `switch`, `pin`).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Installazione verificata di Claude Code | O10.T1 | ✔ |
| Abbonamento, sessione persistente e Remote Control | O10.T2, A6.4 | ✔ |
| Uso reale dalla chat | O10.T4 | ✔ |
| Claude Code a versione fissa con prova degli agganci | O18.T2 | ✔ |
| `deck claude`: sessioni elencate, aperte e chiuse | O15.T2 | ✔ |
| Sessione reale con Remote Control: permessi e strumenti nuovi | O12.T5 (N54) | ✖ da chiudere formalmente (in uso tutti i giorni) |
| Credenziali dell'harness con `deck secrets` cifrati | A6.6, A3.6 | ✖ previsto |

## Issue aperte

- Claude Code 2.1.312 disponibile (avviso `NEWER_AVAILABLE` in `deck claude/version`): l'aggiornamento si fa con
  `probe` e `switch`.
- Le sessioni già aperte non vedono le novità di `deck release install` fino a un riavvio (componente 04).
- Le sessioni nate in un riavvio ripartono con un nuovo id: la continuità dipende dal Brain (componente 13).

## Obiettivi tecnici

1. Passaggio alla 2.1.312 con `probe`.
2. Chiudere O12.T5 annotando cosa funziona già con Remote Control.
