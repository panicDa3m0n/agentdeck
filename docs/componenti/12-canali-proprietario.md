# 12 Canali con il proprietario: la voce

**Stato:** parziale. Le richieste con pagina monouso sono attive; Telegram aspetta il bot; la tabella delle
richieste è prevista. Indice: [README.md](README.md).

## Scopo

Come AgentDeck parla con il proprietario fuori dalle sessioni: chiedere un segreto o una decisione, mandare un
rapporto, ricevere un compito. Il proprietario non è alla macchina e spesso è al telefono.

## Come funziona oggi

- **Richieste con pagina monouso** ([../richieste.md](../richieste.md),
  [../../deck/agentdeck/owner_page.py](../../deck/agentdeck/owner_page.py)). Decisione del proprietario del 30/10
  (INV-5): ogni richiesta genera una pagina HTML semplice, esposta con un tunnel temporaneo di Cloudflare solo fino
  alla risposta, poi tutto si chiude.
  - **`deck secret request name=<segreto>`:** il valore va nel file 600 e l'agente non lo vede. Usato il 30/10 per
    la chiave MiniMax.
  - **`deck ask create`:** domanda con campi, risposta che torna all'agente come dato (`deck ask show`). Provata dal
    vero il 30/10, con una risposta da internet.
- **Ponte Telegram** `agentdeck-telegram` ([../telegram.md](../telegram.md)): long polling senza porte esposte, solo il
  chat id del proprietario; i suoi messaggi diventano compiti dell'agente interno e il rapporto torna in chat.
  Installato e attivo, ma **senza bot**: manca la configurazione (R8).
- **Chat delle sessioni** con Remote Control (componente 07): resta il canale principale.

## Comandi collegati

`deck secret` (`request`, `cancel`), `deck ask` (`create`, `show`, `cancel`), `deck telegram` (`send`).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Ponte Telegram con il proprietario | O21.T1, piano punto 3 | ◐ installato e provato con un finto Telegram; manca il bot vero (R8) |
| Segreti consegnati senza chat | O23.T1 | ✔ |
| Domande al proprietario senza chat | O23.T1 | ✔ |
| Tabella delle richieste in dashboard (`deck requests`) | O19.T2, piano punto 9 | ✖ da rivedere con il proprietario |
| Rapporti dei controlli automatici inviati da soli | O21.T1 | ◐ pronto nel ponte, aspetta il bot e il timer |

## Issue aperte

- R8: token e chat id del bot. Ora si consegnano con `deck secret request name=telegram`.
- `deck ask` serve un link: senza Telegram, un agente di background lo può solo mettere nel suo rapporto.
- Con il tunnel, chiunque abbia il link può aprire la pagina per 15 minuti; Cloudflare vede i valori in transito.

## Obiettivi tecnici

1. Configurare il bot (`deck secret request name=telegram`) e provarlo dal vero.
2. Collegare `deck ask` a Telegram: il link arriva da solo al proprietario.
3. Tabella delle richieste quando il proprietario la rivede.
