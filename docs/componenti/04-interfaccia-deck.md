# 04 Interfaccia agentica `deck`: il sistema nervoso

**Stato:** attivo. Indice: [README.md](README.md).

## Scopo

Il modo in cui un agente usa il sistema: schermate JSON con fatti, azioni, avvisi e un `prompt` che dice il passo
successivo, invece di comandi pensati per un umano (INV-2, INV-4). Tutti gli altri organi si espongono da qui.

## Come funziona oggi

- **Protocollo** ([../protocollo.md](../protocollo.md),
  [../../deck/agentdeck/protocol.py](../../deck/agentdeck/protocol.py)): schermate con `data`, `actions`, `alerts`,
  `nav` e `prompt`. Il canale istruzioni accetta solo testo `SysText` nato da modelli scritti nel codice (INV-4).
  Le azioni distruttive vanno in due passi: anteprima, poi conferma con il codice.
- **Motore** ([../../deck/agentdeck/engine.py](../../deck/agentdeck/engine.py)): indirizzi, parametri tipizzati,
  conferme ed errori. Dal 29/10 lo usa anche `brain` (`Deck(..., command=, obligations=)`).
- **Riga di comando** `deck [indirizzo] [azione] [nome=valore]`; **server MCP** `deck mcp` con uno strumento per
  azione (`mcp__deck__<componente>_<azione>`).
- **Componenti di `deck`:** `/status`, `/network`, `/service`, `/logs`, `/snapshot`, `/update`, `/term`,
  `/obligations`, `/claude`, `/claude/version`, `/release`, `/agent`, `/telegram`, `/secret`, `/ask`, `/protocol`.
  Ognuno è descritto nel componente di sistema a cui appartiene; la tabella completa è in [../deck.md](../deck.md).
- **Schermo:** ogni chiamata scrive una riga nel journal per lo schermo della Deck (componente 08).

## Comandi collegati

`deck`, `deck mcp`, `deck /protocol`; quelli di questo organo in senso stretto sono `deck status`, `deck service`
e `deck logs`.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Specifica del protocollo e autoprompting | O2.T1 | ✔ |
| Motore `deck` e installazione | O2.T2 | ✔ |
| `status`, `snapshot`, `network`, `service`, `logs`, `update` | O3-O6 | ✔ |
| `deck mcp`: `deck` come strumento nativo di Claude Code | O10.T6, A6.2 | ✔ |
| Ambiente delle sessioni per macchine (`PAGER=cat`, `NO_COLOR`, lingua fissa) | A2.1 | ✖ previsto |
| `deck` sulle API native (varlink, D-Bus di iwd, `snapper --jsonout`) | A2.2 | ✖ previsto |
| AgentDeck come servizio varlink `io.agentdeck.*` | A2.3, decisione D5 | ✖ previsto |
| Regia dei comandi grezzi, lavori come unità transitorie (`deck jobs`) | A2.4, A2.5 | ✖ previsto |
| `deck package` (installare, rimuovere, cercare con snapshot e anteprima) | piano punto 4 | ✖ approvato in linea di principio |
| `deck access` (chiavi e `sshd` con rete di sicurezza) | piano punto 4 | ✖ approvato in linea di principio |
| `deck service` anche per i timer (oggi solo unità `.service`) | 30/10, timer dell'agente interno | ✖ emerso il 30/10 |

## Issue aperte

- `deck service` gestisce solo unità `.service`: il 30/10 il timer dell'agente interno si è dovuto fermare con
  `systemctl`.
- La sessione MCP di `deck` resta sul codice della versione con cui è partita: dopo `deck release install` le
  azioni nuove si vedono solo nelle sessioni nuove (da shell `deck` è subito aggiornato).
- I pacchetti si installano ancora con l'adattatore e `pacman` (componente 05): niente `deck package`.

## Obiettivi tecnici

1. `deck package`, poi gli altri componenti del punto 4 solo se servono davvero.
2. Timer in `deck service`.
3. A2.1 (configurazione delle sessioni), poi la decisione D5 (servizio varlink).
