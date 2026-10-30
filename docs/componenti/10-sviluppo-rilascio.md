# 10 Sviluppo e rilascio: la crescita

**Stato:** attivo. Indice: [README.md](README.md).

## Scopo

AgentDeck lo sviluppano gli agenti sulla Deck stessa (piano punto 10): repository, test, installazione con ritorno
indietro, versioni pubblicate su GitHub (INV-8), documentazione insieme al codice (INV-9).

## Come funziona oggi

- **Repository** `/home/agent/agentdeck/repo`, remote privato `panicDa3m0n/agentdeck`. Si pubblica dalla Deck con il
  login `gh` del proprietario (ADR-0002), senza mai leggere il token ([../sviluppo.md](../sviluppo.md)).
- **`deck release install`** ([../../deck/agentdeck/release.py](../../deck/agentdeck/release.py)):
  1. estrae il commit e lancia i test;
  2. scatta uno snapshot;
  3. scambia in modo atomico `/opt/agentdeck`, che è un collegamento alla versione;
  4. esegue i passi di sistema: comandi `deck` e `brain`, hook, unità, configurazione di Claude Code, server MCP;
  5. verifica, e se qualcosa fallisce torna da solo alla versione di prima.
  `deck release revert` torna indietro. Si tengono le ultime 5 versioni.
- **Versioni:** MAJOR.MINOR.PATCH in `VERSION`, storia in [../../CHANGELOG.md](../../CHANGELOG.md), un tag annotato
  `v<versione>` per ogni versione chiusa (0.5.14 il 30/10).
- **Versioni fissate:** Claude Code e ogni installazione fuori da pacman (componenti 06 e 07).
- **Metodo:** dal 30/10 si lavora per componenti, con queste schede. La governance `wf.sh` è spenta: i suoi file
  restano per controllo.

## Comandi collegati

`deck release` (`install`, `revert`), `git`, `gh`, test con `cd deck && python3 -m unittest discover -s tests`.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Identità git e remote privato | O1.T1 | ✔ |
| Documentazione indicizzata e collegata al codice | O1.T4, INV-9 | ✔ |
| Il lavoro dell'agente sulla Deck arriva nel repository | O14 | ✔ |
| Sviluppo sulla Deck, installazione e revert da qui | O18.T1, piano punto 10 | ✔ |
| Le note di `~/agentdeck/consegna/` portate nel repository | piano punto 10 | ◐ in parte (piano, documenti); la cartella esiste ancora |
| Indice dei componenti al posto della governance | decisione del 30/10 | ✔ questo indice |

## Issue aperte

- Trappole P25 e P26: passi nuovi di verifica ed estrazione compaiono solo alla seconda installazione, perché li
  esegue la versione che lancia.
- La sessione che installa non vede subito le novità nei suoi strumenti MCP (componente 04).
- I file in `~/agentdeck/consegna/` sono doppioni parziali dei documenti.

## Obiettivi tecnici

1. Mantenere le schede dei componenti aggiornate a ogni commit.
2. Chiudere la cartella `consegna/` quando il suo contenuto è tutto in `docs/`.
