# 03 Reversibilità: snapshot, aggiornamenti, backup. Il sistema immunitario

**Stato:** parziale. Snapshot e aggiornamenti sono attivi; il backup fuori dalla Deck e la politica degli snapshot
sono previsti. Indice: [README.md](README.md).

## Scopo

Ogni modifica deve poter tornare indietro (INV-3), e un guasto del disco o della Deck non deve far perdere il
lavoro: snapshot, aggiornamenti protetti, copie fuori dalla macchina.

## Come funziona oggi

- **Snapper**, configurazione `root` sul solo subvolume `@`, con timeline e pulizia. `snap-pac` scatta uno snapshot
  prima e uno dopo ogni transazione di pacman (oltre 100 snapshot il 30/10).
- **`deck snapshot`:** elenco, `create description=…`, `rollback id=…` con anteprima e conferma
  ([../../deck/agentdeck/components/snapshot.py](../../deck/agentdeck/components/snapshot.py)). Dopo un rollback
  anche `/opt/agentdeck` torna alla versione dello snapshot (trappola P9).
- **`deck update`:** `check`, poi `apply` con anteprima (snapshot prima e dopo), poi `verify` (accesso, `sshd`, DNS,
  servizi falliti) e `reboot` quando serve. Provato davvero (O9, O11) e usato di nuovo il 30/10: 8 pacchetti,
  snapshot 215 e 218, verifica a posto.
- **Cosa non torna indietro:** `@home` (dove stanno il repository, le memorie del Brain e le sessioni), `@log`,
  `@servizi`. Un rollback del sistema non li tocca, ma nessuno li fotografa.

## Comandi collegati

`deck snapshot` (`create`, `rollback`), `deck update` (`check`, `apply`, `verify`, `reboot`), `deck release revert`
per la sola versione di AgentDeck (componente 10).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| `deck snapshot`: elenco, creazione, rollback con anteprima | O3.T2, O3.T3 | ✔ |
| Pulizia dei vecchi sistemi lasciati dai rollback | O7.T2 | ✔ |
| `deck update` con anteprima, snapshot, verifica e riavvio | O6, O9, O11 | ✔ provato davvero |
| Politica degli snapshot (pulizia `number`, `important`, quote) | A4.1 | ✖ previsto |
| "Stati buoni": snapshot confermati da un avvio o da una verifica | A4.2 | ✖ previsto (con A1.6, componente 01) |
| Stato voluto come dato (`deck state`) | A4.3, decisione D4 | ✖ previsto |
| Transazioni di pacman registrate, `.pacnew` come obblighi | A4.4 | ◐ l'hook di pacman esiste ma apre solo gli obblighi dei profili (componente 05) |
| Notizie di Arch lette prima di aggiornare | A4.5 | ✖ previsto |
| Snapshot dei dati dei servizi (`@servizi`) | O13.T2 | ✖ |
| Copia del database del Brain | N71, O22.T4 | ✖ |
| **Backup fuori dalla Deck**: peso, blocchi, repository GitHub dedicato con gli ultimi 1-2, cifrati (INV-6) | piano punto 2 | ✖ previsto, alla fine del piano |

## Issue aperte

- Niente protegge `@home` e `@servizi`: un errore nel repository locale o nei dati di un servizio si recupera solo
  da GitHub (per il codice) o non si recupera.
- `deck update reboot` lo può chiamare chiunque abbia `deck`: il 30/10 l'agente interno l'ha usato da solo
  (componenti 06 e 11).

## Obiettivi tecnici

1. Configurazioni snapper per `@home` (o almeno per le cartelle di AgentDeck) e per `@servizi`.
2. Backup cifrato fuori dalla Deck (punto 2), dopo il safe mode (componente 01).
3. A4.1 e A4.2 insieme all'avvio di prova.
