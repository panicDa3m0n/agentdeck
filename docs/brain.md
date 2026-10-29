# Il Brain: la memoria dell'agente (`brain`)

Il Brain è il componente di AgentDeck dedicato al "cervello" dell'agente, tra il sistema e il modello: i processi
interni dell'agente, a partire dalla memoria. È separato da `deck`, che lavora sul sistema (OS, hardware, software):
`brain` ha solo operazioni interne dell'agente. Origine: piano punto 7 ([piano.md](piano.md)), obiettivo O22.
Indice: [README.md](README.md).

Stato: **O22.T1 fatto** (comando, server MCP, memoria con ricerca testuale). Da fare: i pacchetti di contesto
automatici (O22.T2), la ricerca ibrida con embedding e reranker locali (O22.T3), la manutenzione ciclica (O22.T4).

## Comando e server MCP

| Come | Cosa |
|---|---|
| `brain [indirizzo] [azione] [nome=valore ...] [--pretty]` | Riga di comando, come `deck`: ogni risposta è una schermata JSON del protocollo ([protocollo.md](protocollo.md)) |
| `brain mcp` | Server MCP su stdio: strumenti `mcp__brain__open` e `mcp__brain__<componente>_<azione>`, risorse `brain:<indirizzo>` |
| `brain` (indirizzo `/`) | Schermata principale: i componenti del Brain |
| `brain /memory` | La memoria: conteggi, ultime memorie attive, tipi, azioni |

`brain` usa lo stesso motore di `deck` ([deck.md](deck.md)): indirizzi, parametri tipizzati, conferme in due passi,
errori, validazione delle schermate e canale istruzioni separato dai dati (INV-4). Le differenze:
- i testi del sistema citano `brain`, non `deck` (`Deck(..., command="brain")` in
  [../deck/agentdeck/engine.py](../deck/agentdeck/engine.py));
- le schermate di `brain` non portano il campo `obligations`, che resta di `deck` (protocollo, sezione 6 bis);
- sullo schermo della Deck una chiamata compare come `brain /memory search: ok`
  ([schermo.md](schermo.md)); i parametri, e quindi i testi delle memorie, non vanno nel journal.

**Componenti isolati.** Ogni componente del Brain è un modulo suo in
[../deck/agentdeck/brain/components/](../deck/agentdeck/brain/components/__init__.py), con la logica in un modulo a
parte che non conosce il protocollo. Un database guasto dà una schermata di errore solo su `/memory`: la schermata
principale e, nel server MCP, gli strumenti degli altri componenti restano in piedi. La verifica di
`deck release` controlla che `brain` e `brain mcp` partano, non lo stato del database: un problema della memoria
non fa tornare indietro il sistema.

## La memoria (`/memory`, O22.T1)

### Il pacchetto

Una memoria è un pacchetto JSON piccolo:

```json
{"id": 12, "type": "decision", "status": "active",
 "text": "Per scegliere le memorie si usa solo un reranker cross-encoder multilingue, non Laya (proprietario, 29/10)",
 "tags": ["brain", "reranker"],
 "origin": {"session": "7ecf5338-…", "message": "1111bf1c-…"},
 "revision": 1, "created": "2026-10-29T23:50:00+01:00", "updated": "2026-10-29T23:50:00+01:00",
 "links": {"supersedes": [], "superseded_by": null, "merged_from": [], "merged_into": null}}
```

| Campo | Regola |
|---|---|
| `type` | `fact` (com'è una cosa), `decision` (cosa si è deciso e perché), `preference` (come vuole le cose il proprietario), `procedure` (come si fa), `lesson` (un errore da evitare), `reference` (dove trovare qualcosa) |
| `text` | Un'idea sola, comprensibile da sola, al massimo 1000 caratteri; spazi ai bordi e caratteri di controllo tolti |
| `tags` | Al massimo 8, in minuscolo: lettere, cifre, punto, trattino, trattino basso; fino a 32 caratteri |
| `status` | `active`, `deprecated` (non vale più), `superseded` (sostituita da un'altra), `merged` (accorpata in un'altra) |
| `origin` | Sessione di Claude Code e messaggio in cui è nata la memoria (vedi sotto) |
| `revision` | Sale a ogni cambiamento; ogni versione resta nelle revisioni |
| `links` | Collegamenti per id: chi sostituisce chi, chi è nata dall'accorpamento di chi |

**Nessun segreto (INV-6).** `save`, `edit` e `merge` rifiutano un testo che sembra contenere un segreto: chiavi
private, token GitHub, Anthropic, Slack, Telegram, chiavi AWS, JWT, `password=…` o `token: …` seguiti da un valore.
L'errore dice in `data.pattern` cosa sembrava un segreto, mai il segreto. Si scrive dove sta il segreto (`token:
~/.config/agentdeck/telegram.json` passa: un percorso non è un segreto), mai il suo valore.

### Le azioni

| Azione | Effetto | Cosa fa |
|---|---|---|
| `search` | read | Ricerca testuale su testo ed etichette, ordinata per bm25; senza `query`, le memorie cambiate più di recente. Filtri: `type`, `tag`, `status` (`active` di norma, oppure `deprecated`, `superseded`, `merged`, `all`), `limit` (1-50, 10 di norma) |
| `show` | read | Una memoria con i collegamenti e tutte le revisioni, dalla più recente |
| `save` | safe | Una memoria nuova, con l'origine presa da sé; risponde anche con `data.similar`, fino a 3 memorie attive con parole in comune, per accorpare o sostituire invece di tenere doppioni |
| `edit` | safe | Cambia testo, tipo o etichette di una memoria attiva; la versione di prima resta nelle revisioni |
| `deprecate` | safe | Una memoria che non vale più esce dalle ricerche; il motivo è obbligatorio |
| `restore` | safe | Torna attiva una memoria deprecata, sostituita o accorpata; il collegamento che la chiudeva sparisce, e resta nelle revisioni |
| `supersede` | safe | `id` è sostituita da `by` (attiva): la vecchia si chiude, il collegamento resta in tutte e due |
| `merge` | safe | Accorpa 2-10 memorie attive in una nuova scritta dall'agente: le vecchie si chiudono come `merged`, collegate alla nuova. Il tipo, se manca, è quello comune; le etichette, se mancano, l'unione |
| `forget` | destructive | Cancella davvero memoria, revisioni e collegamenti, con anteprima e codice di conferma. Solo per un segreto o un dato personale salvato per errore: per ritirare una memoria si usa `deprecate` |

Ogni cambiamento registra nella revisione il motivo (`reason`, facoltativo tranne che per `deprecate`) e la
sessione che l'ha fatto. Solo `forget` toglie qualcosa: con `secure_delete`, l'ottimizzazione dell'indice e
`VACUUM`, il testo non resta nemmeno nelle pagine libere del file.

### Ricerca testuale

SQLite con FTS5 (tokenizzatore `unicode61` senza accenti, quindi "perché" trova "perche"). La domanda libera
diventa una ricerca sicura: parole tra virgolette in OR, così la sintassi di FTS5 (`NEAR`, `*`, virgolette) non
passa; le parole di 5 lettere o più cercano anche il prefisso senza l'ultima lettera, così "memorie" trova
"memoria". Le etichette pesano il doppio del testo. `score` è il bm25 cambiato di segno: più alto è meglio, e vale
solo tra i risultati della stessa ricerca. È la parte testuale della ricerca ibrida di O22.T3.

### Origine

La sessione viene da `CLAUDE_CODE_SESSION_ID`, che Claude Code passa ai comandi e ai server MCP che lancia; il
messaggio è l'ultima richiesta vera nella trascrizione della sessione (`~/.claude/projects/<cartella>/<sessione>.jsonl`:
l'ultima riga `user` che non è un risultato di strumento né un messaggio meta), letta dalla fine. Della trascrizione
si leggono solo forma delle righe e `uuid`. `save` accetta `session` e `message` espliciti, per salvare a nome di
un'altra sessione; fuori da Claude Code l'origine resta vuota. Codice:
[../deck/agentdeck/brain/origin.py](../deck/agentdeck/brain/origin.py).

### Dove sta

`~/.local/share/agentdeck/brain/brain.db` (cartella 700, file 600), oppure `$AGENTDECK_BRAIN_DB`. SQLite in modo
WAL con attesa sui blocchi: più sessioni, ognuna con il suo `brain mcp`, scrivono insieme. La versione dello schema
sta in `PRAGMA user_version`; un database più nuovo del codice viene rifiutato.

**Snapshot.** `/home` è il sottovolume `@home`, che snapper non fotografa (la configurazione `root` copre solo `/`).
Così un rollback del sistema non cancella le memorie, ma il database non ha ancora snapshot né copie: per ora lo
proteggono solo le revisioni. La protezione (copia periodica o configurazione snapper sua) è di O22.T4.

## INV-4: le memorie sono dati

Le memorie le scrivono gli agenti e possono nascere da testo esterno (log, pagine web, output di programmi). Per
questo stanno solo in `data`: titoli, prompt, etichette delle azioni e messaggi di errore nascono da modelli scritti
nel codice, con dentro solo numeri e identificatori validati. Le istruzioni del server MCP e la regola in
[../deck/claude/CLAUDE.template.md](../deck/claude/CLAUDE.template.md) dicono all'agente che un testo di memoria è
un'informazione da verificare sullo stato attuale, mai un'istruzione. Quando O22.T2 porterà le memorie nel contesto
da sé, ci arriveranno come dati etichettati.

## Come lo usano gli agenti

- **Sessioni di Claude Code:** il server MCP `brain` è registrato per l'utente `agent` da `deck release install`
  (passo "claude mcp brain"), le impostazioni gestite permettono gli strumenti `mcp__brain`
  ([../deck/claude/managed-settings.json](../deck/claude/managed-settings.json)); la regola "Memory is `brain`" del
  `CLAUDE.md` di sistema dice quando cercare e cosa salvare ([claude-code.md](claude-code.md)).
- **Agente interno:** `deck agent run` gli passa anche il server `brain`; può cercare e salvare, e propone soltanto
  `forget` ([agente-interno.md](agente-interno.md)).
- La memoria a file di Claude Code (`~/.claude/projects/<cartella>/memory/`) resta com'è finché O22.T2 non porta le
  memorie del Brain nel contesto da sé.

## Codice e test

| File | Cosa contiene |
|---|---|
| [../deck/brain](../deck/brain) | Il comando `brain`, installato come `/usr/local/bin/brain` |
| [../deck/agentdeck/brain/__init__.py](../deck/agentdeck/brain/__init__.py) | Il motore con i componenti del Brain e le istruzioni del server MCP |
| [../deck/agentdeck/brain/cli.py](../deck/agentdeck/brain/cli.py) | Riga di comando e `brain mcp` |
| [../deck/agentdeck/brain/memory.py](../deck/agentdeck/brain/memory.py) | Archivio: schema SQLite, FTS5, validazione, segreti, revisioni, collegamenti |
| [../deck/agentdeck/brain/origin.py](../deck/agentdeck/brain/origin.py) | Sessione e messaggio di origine dalla trascrizione |
| [../deck/agentdeck/brain/components/memory.py](../deck/agentdeck/brain/components/memory.py) | La schermata `/memory` e le sue azioni |
| [../deck/agentdeck/brain/components/home.py](../deck/agentdeck/brain/components/home.py) | La schermata principale di `brain` |
| [../deck/tests/test_brain.py](../deck/tests/test_brain.py) | Test: archivio, segreti, ricerca, revisioni, collegamenti, `forget` senza tracce, concorrenza, origine, schermate, errori, conferme, MCP, INV-4 |

Si aggiunge un componente al Brain come a `deck` ([deck.md](deck.md), "Aggiungere un componente"), ma nella cartella
`agentdeck/brain/components/` e nell'elenco del suo `__init__.py`.
