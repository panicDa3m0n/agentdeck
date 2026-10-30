# 09 Servizi ospitati: gli organi del proprietario

**Stato:** parziale. Indice: [README.md](README.md).

## Scopo

La Deck ospita i servizi del proprietario, ognuno isolato nella sua cartella e con la sua unità. Sono **del
proprietario** (ADR-0001): codice, configurazione, dati, segreti e l'avvio delle unità li decide lui, e la guardia
ferma l'agente con il motivo.

## Come funziona oggi

- **Area** `/srv/servizi/<nome>`, nel subvolume `@servizi`; un utente di sistema per servizio; unità
  `agentdeck-servizio@<nome>` ([../servizi.md](../servizi.md), [../../servizi/](../../servizi/install-servizi.sh)).
- **Servizi presenti il 30/10:** `domus`, attivo (unità `agentdeck-servizio@domus` in esecuzione; token Baxi nei suoi
  segreti, N64).
- **Gestione:** `deck service` vede l'unità solo mentre è caricata; la guardia rifiuta all'agente avvio, arresto e
  abilitazione delle unità dei servizi.

## Comandi collegati

`deck service` e `deck service show name=agentdeck-servizio@<nome>`; azioni sulle unità solo per il proprietario.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Area dei servizi con isolamento e rete | O10.T12 | ✔ |
| Servizi del proprietario protetti dalla guardia | O12.T1, O19.T1 | ✔ |
| `deck servizi`: elenco, crea, aggiorna da git, rimuovi con anteprima | O13.T1 (N53, N56) | ✖ |
| Snapshot dei dati dei servizi (`@servizi`) | O13.T2 | ✖ |
| Firewall con le porte dei servizi esposti per decisione | O13.T3 | ✖ (componente 02) |
| Il primo servizio vero, scelto dal proprietario | O13.T4 | ◐ `domus` gira, nato da una sessione e non da `deck servizi` |
| Servizi in container o portabili | A4.7 | ✖ previsto, più avanti |

## Issue aperte

- Un servizio fermo non compare in `deck service`.
- I dati dei servizi non hanno snapshot né copie.
- Il 30/10 il riavvio fatto dall'agente interno ha fermato anche i servizi e i lavori lunghi di altre sessioni (memoria
  5 di `brain`, progetto `frugale`).

## Obiettivi tecnici

1. `deck servizi` (O13.T1) con snapshot dei dati (O13.T2).
2. Un riavvio annunciato ai servizi e alle sessioni prima di farlo (componenti 03 e 11).
