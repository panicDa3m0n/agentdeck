# 08 Schermo e interfacce effimere: il volto

**Stato:** parziale. Indice: [README.md](README.md).

## Scopo

Lo schermo della Deck mostra cosa succede, per chi passa davanti: calmo di norma, con interfacce effimere quando
servono. Le sette regole dello stile sono in [../interfacce.md](../interfacce.md).

## Come funziona oggi

- **Schermo grafico** (decisione ADR-0003): `cage` + Chromium in kiosk, servizio `agentdeck-ui`, con le pagine
  locali servite da `deck ui` (`agentdeck-ui-server`, porta 8777). La prima interfaccia mostra le sessioni Claude
  ([../../deck/ui/index.html](../../deck/ui/index.html), [../../deck/agentdeck/ui.py](../../deck/agentdeck/ui.py)).
  Attivo il 30/10.
- **Schermo terminale** ([../schermo.md](../schermo.md), [../../deck/screen/](../../deck/screen/agentdeck_screen.py)):
  ogni comando dell'agente, la sua risposta e l'esito di `deck` e `brain`, come un terminale. Il servizio
  `agentdeck-screen` è spento dal 30/10: al suo posto c'è lo schermo grafico.
- `deck release install` rifiuta i cambi a `screen/` e `ui/`, perché la loro installazione tocca la configurazione di
  SSH; si installano con `deck/install.sh` dal Mac.

## Comandi collegati

Servizi `agentdeck-ui` e `agentdeck-ui-server`; `deck claude` (stessi dati della pagina).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Attività dell'agente visibile come un terminale, con le risposte | O3.T4, O3.T5 | ✔ (oggi spento) |
| Schermo leggibile e modalità compatta | O7.T1 | ✔ |
| Stile delle interfacce effimere e tecnologia grafica | O15.T1 | ✔ |
| La schermata delle sessioni Claude | O15.T2 | ✔ |
| Schermo grafico calmo con l'interfaccia effimera delle sessioni | O15.T3 | ◐ installato e attivo; manca la prova al tocco con il proprietario alla Deck |
| Altre interfacce effimere (avvisi, richieste…) | [../interfacce.md](../interfacce.md) | ✖ previste |

## Issue aperte

- O15.T3: la prova al tocco richiede il proprietario alla Deck.
- La pagina ascolta su `0.0.0.0:8777`, raggiungibile da tutta la LAN (piano punto 6: fuori ambito; il firewall è
  del componente 02).
- L'installazione di `screen/` e `ui/` passa ancora dal Mac.

## Obiettivi tecnici

1. Prova al tocco quando il proprietario è alla Deck.
2. Una procedura di `deck release` per `screen/` e `ui/` con verifica dell'accesso (INV-1).
