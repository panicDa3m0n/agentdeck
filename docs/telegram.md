# Telegram

Il canale a due vie fra il proprietario e AgentDeck. Decisione del proprietario del 29/10/2026, piano punto 3
([piano.md](piano.md)): un solo canale, una chat continua con AgentDeck. Dentro, ogni messaggio apre una corsa breve
dell'agente interno ([agente-interno.md](agente-interno.md)). Obiettivo O21 della governance. Indice:
[README.md](README.md).

## Come funziona

[../deck/agentdeck/telegram.py](../deck/agentdeck/telegram.py), servizio
[../deck/claude/agentdeck-telegram.service](../deck/claude/agentdeck-telegram.service), utente `agent`.
- **Nessuna porta esposta (INV-5).** Il ponte chiede gli aggiornamenti al bot con long polling (`getUpdates`, 50 s).
- **Solo il proprietario.** Risponde solo al `chat_id` configurato. Gli altri mittenti sono ignorati e registrati in
  `~/.local/state/agentdeck/telegram-unknown.jsonl`; `deck telegram` li mostra come dati.
- **Messaggi del proprietario.** Un testo diventa il compito di una corsa dell'agente interno (`deck agent run`). Il
  ponte risponde "Ricevuto" e poi manda il rapporto. Una corsa alla volta. L'offset si salva prima di eseguire,
  così un compito non si ripete dopo un riavvio.
- **Comandi:** `/stato` manda un riassunto di `deck status` (versione, avvisi, temperatura, batteria, servizi
  falliti) senza chiamare il modello; `/help` li elenca.
- **Rapporti automatici.** I rapporti dei controlli del timer ([agente-interno.md](agente-interno.md)) arrivano da
  soli. Alla prima accensione non si rimanda la storia.
- **Messaggi lunghi** divisi in parti da 3900 caratteri.

**`deck telegram`** ([../deck/agentdeck/components/telegram.py](../deck/agentdeck/components/telegram.py)) mostra se il
bot è configurato, se il ponte è attivo e i mittenti sconosciuti. `deck telegram send text=<messaggio>` scrive al
proprietario: per esempio un agente che vuole avvisarlo di qualcosa.

## Configurazione

Il proprietario crea il bot con BotFather e scrive sulla Deck `~/.config/agentdeck/telegram.json`, permessi 600:

```json
{"token": "<token del bot>", "chat_id": <il proprio chat id>}
```

Il token non entra mai nel repository (INV-6), né nei registri, né negli errori (l'URL dell'API lo contiene, quindi
gli errori riportano solo il tipo). Senza il file il servizio aspetta e riprova ogni minuto; quando il file cambia il
ponte riparte da solo. `deck release install` installa, abilita e riavvia il servizio.

## Prove

[../deck/tests/test_telegram.py](../deck/tests/test_telegram.py), contro un finto server della Bot API su 127.0.0.1:
compito e rapporto, offset, mittenti sconosciuti, `/stato` e `/help`, rapporti automatici mandati una volta sola,
divisione dei messaggi lunghi, token mai negli errori, configurazione, schermata. La prova con il bot vero si fa quando
c'è il token (richiesta R8 della governance).

## Da fare

Conferme con pulsanti (approvare dalla chat le proposte dei rapporti) e il cruscotto in un'app propria restano idee
del piano, da decidere insieme.
