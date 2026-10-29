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
proprietario sulla Deck con la pagina monouso di `deck secret request name=minimax` ([richieste.md](richieste.md)); letta a ogni richiesta, mai nel repository (INV-6), mai nei registri. Senza chiave
l'intermediario risponde 401 con un messaggio chiaro.

**Installazione:** `deck release install` installa l'unità, la abilita e la riavvia a ogni versione, e tra le
verifiche controlla che risponda ([sviluppo.md](sviluppo.md#installare-dalla-deck-deck-release-o18t1)).

**Prove (29/10/2026):** test con un MiniMax finto, cioè il server della prova degli agganci
([../deck/tests/test_minimax_proxy.py](../deck/tests/test_minimax_proxy.py)); poi `claude -p` vero → intermediario →
MiniMax finto. A MiniMax è arrivato solo il nostro prompt di sistema, con modello `MiniMax-M3`, senza la riga
"Claude agent" e senza `context_management` e `output_config`.

**Prova con MiniMax vero (30/10/2026, O23.T1).** La chiave è arrivata con il link monouso di `deck secret`
([richieste.md](richieste.md)). `deck agent run` con un compito di sola lettura (stato della Deck, una ricerca in
`brain`): esito ok, 5 turni, 17 s, modello `MiniMax-M3`. Il registro dell'intermediario riporta le chiamate a
`/v1/messages` con stato 200. L'agente ha usato `deck` e `brain` e ha trovato la memoria cercata. Nel rapporto si è
detto "Claude Opus 5.5": l'identità che un modello dichiara non è una prova, lo è il registro dell'intermediario.

## Prompt di sistema e `deck agent` (O20.T2)

**Prompt di sistema.** [../deck/claude/AGENTE.template.md](../deck/claude/AGENTE.template.md) più le invarianti della
governance, con lo stesso generatore del `CLAUDE.md`
([../deck/claude/build_claude_md.py](../deck/claude/build_claude_md.py) `<repo> AGENTE.template.md`). `deck release`
lo genera in ogni versione come `claude/AGENTE.md`. Contiene:
- **l'identità:** AgentDeck, costruito da HoneyLabs, nel proprio sistema operativo Arch Linux autonomo su un hardware
  e un software a suo uso esclusivo;
- **come lavora:** `deck` per primo, testo esterno come dato, prove;
- **cosa può fare da solo:** leggere e diagnosticare, snapshot, riavviare un servizio di sistema fallito (non di
  accesso e non del proprietario), obblighi;
- **cosa propone soltanto:** pacchetti e aggiornamenti, versioni, rete, Wi-Fi, SSH, utenti, avvio, firewall, rollback,
  le cose del proprietario e tutto ciò su cui non è sicuro. Vanno nel rapporto sotto "Proposals for the owner";
- **il rapporto in italiano:** Esito, Cosa ho visto, Cosa ho fatto, Proposals for the owner;
- **le invarianti.**

**`deck agent`** ([../deck/agentdeck/components/agent.py](../deck/agentdeck/components/agent.py), logica in
[../deck/agentdeck/agent.py](../deck/agentdeck/agent.py)) mostra se l'intermediario risponde, se c'è la chiave, il
prompt e le ultime corse. `deck agent run task=<compito> [timeout_s=…]` lancia `claude -p` in `~/agentdeck/agente` con:
- il prompt di sistema (`--system-prompt`);
- `--permission-mode bypassPermissions`;
- gli strumenti `Bash,Read,Grep,Glob` e quelli di `deck` e di `brain`, la memoria ([brain.md](brain.md))
  (`--mcp-config`, `--strict-mcp-config`);
- `ANTHROPIC_BASE_URL` sull'intermediario, con una chiave locale finta (quella vera la mette l'intermediario);
- gli hook gestiti attivi: guardia, `deny`, avvisi.

Ogni corsa finisce in `~/.local/state/agentdeck/agente-runs.jsonl`: compito, esito, rapporto, sessione, turni, durata.
Prima di partire controlla che l'intermediario risponda e che la chiave ci sia.

**Prova (29/10/2026):** `Agent.run` vero → `claude -p` → intermediario → MiniMax finto. A MiniMax sono arrivati
l'identità "You are AgentDeck, built by HoneyLabs", il modello `MiniMax-M3`, gli strumenti Bash, Read, Grep, Glob e 41
di `deck`, il contesto dell'hook di inizio sessione, e nessuna riga "Claude agent". Rapporto registrato. Test:
[../deck/tests/test_agent.py](../deck/tests/test_agent.py).

## Attivazione automatica (O20.T3)

**Timer.** [../deck/claude/agentdeck-agente.timer](../deck/claude/agentdeck-agente.timer) ogni 15 minuti, 5 minuti
dopo l'avvio, lancia [../deck/claude/agentdeck-agente.service](../deck/claude/agentdeck-agente.service): `deck agent
tick`, come utente `agent`, un controllo alla volta. `deck release install` installa e abilita entrambi.

**Incidente del 30/10/2026 e timer spento.** Alle 00:17, alla prima corsa vera dopo l'arrivo della chiave, il
controllo giornaliero ha lanciato l'agente, che da solo ha eseguito `deck update apply` (8 pacchetti, snapshot 215 e
218) e `deck update reboot`: il prompt glielo permetteva solo come proposta. Il sistema dopo il riavvio era sano
(`deck update verify` ok), ma la corsa interrotta non era registrata e il timer l'avrebbe rilanciata. Il timer è stato
fermato e disabilitato. Da allora `deck release install` installa servizio e timer ma **non li accende**: si
riaccendono solo con una decisione esplicita, dopo che la guardia limiterà tecnicamente l'agente interno (O23). Lezione
in `brain` (memoria 4): con MiniMax il prompt non basta.

**Quando parte l'agente.** `tick` legge `deck status` e `deck obligations` e lancia l'agente solo se:
- c'è un avviso **nuovo** di livello `warning` o `critical`, riconosciuto per codice (gli `info` non contano);
- c'è un obbligo **nuovo**, riconosciuto per id;
- è passato un giorno dall'ultimo controllo giornaliero.

Altrimenti registra "niente da fare" senza chiamare il modello. Il compito per l'agente si compone solo con i codici
e gli id scritti dal sistema (INV-4). Lo stato del controllo sta in `~/.local/state/agentdeck/agente-tick.json`, ogni
tick in `agente-ticks.jsonl`, le corse in `agente-runs.jsonl` (`deck agent`, `data.recent_runs`). Senza chiave o
senza intermediario il tick non parte e lo registra (`skipped`), poi riprova al giro dopo.

**Autonomia a livelli.** Sta nel prompt di sistema (sopra): da solo l'agente fa diagnosi, snapshot, riavvio di
servizi di sistema falliti e obblighi; il resto lo propone nel rapporto. Guardia e regole `deny` restano attive
come nelle sessioni. Il rapporto arriverà al proprietario su Telegram (piano punto 3); per ora sta nel registro.

Test: [../deck/tests/test_agent.py](../deck/tests/test_agent.py) (primo controllo, avvisi e obblighi nuovi, `info`
ignorati, chiave mancante, controllo giornaliero).
