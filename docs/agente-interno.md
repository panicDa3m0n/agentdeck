# Agente interno

L'agente che vive sulla Deck e lavora da solo, senza che il proprietario apra una sessione: si attiva per eventi e a
intervalli, usa gli stessi strumenti `deck`, la stessa guardia e gli stessi snapshot delle sessioni Claude Code, e
lascia traccia di ogni azione. Decisione del proprietario del 29/10/2026, piano punto 1 ([piano.md](piano.md));
obiettivo O20 della governance. Indice: [README.md](README.md).

## Scelte

- **Modello:** MiniMax via API cloud (INV-7), con l'abbonamento del proprietario. L'endpoint compatibile con
  Anthropic è `https://api.minimax.io/anthropic` e il modello documentato ufficialmente è `MiniMax-M3` (verificato
  sul sito di MiniMax il 29/10/2026). "M3.1" compare solo in fonti di terzi (`MiniMax-M3.1-Flash-Preview`): si
  conferma con la chiave e si imposta in `agente.json`.
- **Motore:** Claude Code headless (`claude -p`), non `--bare`: `--bare` salta tutti gli hook, compresa la guardia
  (verificato il 29/10/2026). Così l'agente interno ha da subito strumenti `deck`, guardia, regole `deny` e hook.
- **Identità:** verso MiniMax non va nessuna identità "Claude". L'agente è AgentDeck, costruito da HoneyLabs, dentro
  il proprio sistema operativo Arch Linux autonomo, integrato in un hardware e un software a uso esclusivo
  dell'agente. Il prompt di sistema lo scrive il sistema (O20.T2, INV-4).

## Intermediario (O20.T1)

[../deck/agentdeck/minimax_proxy.py](../deck/agentdeck/minimax_proxy.py), servizio
[../deck/claude/agentdeck-agente-proxy.service](../deck/claude/agentdeck-agente-proxy.service), solo su
`127.0.0.1:8791`. Claude Code dell'agente interno usa `ANTHROPIC_BASE_URL=http://127.0.0.1:8791`; per ogni richiesta
l'intermediario:
1. toglie dal prompt di sistema la riga fissa di Claude Code ("You are a Claude agent, built on Anthropic's Claude
   Agent SDK." e varianti) e l'intestazione `x-anthropic-billing-header`;
2. imposta il modello configurato;
3. toglie i parametri (`context_management`, `output_config`, `metadata`) e le intestazioni (`anthropic-beta` e
   simili) che MiniMax non usa; l'elenco è configurabile, da rivedere con la prova reale;
4. inoltra a MiniMax con la chiave, mandata come `x-api-key` e come `Authorization: Bearer`;
5. restituisce la risposta in streaming così com'è.

`count_tokens` si stima in locale. I messaggi non si toccano. `GET /health` dice se l'intermediario risponde e se la
chiave c'è. Il registro, `~/.local/state/agentdeck/agente-proxy.jsonl`, tiene solo ora, percorso, modello, esito e
durata: niente contenuti, niente chiave.

**Configurazione**, `~/.config/agentdeck/agente.json`, tutta facoltativa: `upstream`, `model`, `key_file`, `port`,
`strip_params`, `strip_headers`, `timeout_s`. **Chiave:** `~/.config/agentdeck/minimax.key`, permessi 600, scritta dal
proprietario sulla Deck; letta a ogni richiesta, mai nel repository (INV-6), mai nei registri. Senza chiave
l'intermediario risponde 401 con un messaggio chiaro.

**Installazione:** `deck release install` installa l'unità, la abilita e la riavvia a ogni versione, e tra le
verifiche controlla che risponda ([sviluppo.md](sviluppo.md#installare-dalla-deck-deck-release-o18t1)).

**Prove (29/10/2026):** test con un MiniMax finto, cioè il server della prova degli agganci
([../deck/tests/test_minimax_proxy.py](../deck/tests/test_minimax_proxy.py)); poi `claude -p` vero → intermediario →
MiniMax finto. A MiniMax è arrivato solo il nostro prompt di sistema, con modello `MiniMax-M3`, senza la riga
"Claude agent" e senza `context_management` e `output_config`. Prova con MiniMax vero: quando c'è la chiave
(richiesta R7 della governance).

## Da fare

- **O20.T2:** prompt di sistema AgentDeck e `deck agent run`, che lancia l'agente su un compito.
- **O20.T3:** attivazione per eventi e a intervalli, autonomia a livelli (da solo solo diagnosi e azioni a basso
  rischio, le altre segnalate), registro.
