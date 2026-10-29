# Richieste al proprietario: segreti e domande con una pagina monouso (`deck secret`, `deck ask`)

Come l'agente chiede qualcosa al proprietario quando la chat non va bene o non c'è: un segreto (la chiave API di
MiniMax, il token del bot Telegram, qualunque altra chiave) o una domanda (una scelta, un dato, un parere). Nasce
dalle richieste del proprietario del 30/10/2026, obiettivo O23, task O23.T1. Indice: [README.md](README.md).

## La decisione del proprietario (30/10/2026, INV-5)

> Ogni richiesta al proprietario, segreta o no, genera una pagina HTML semplice, esposta su internet con un tunnel
> temporaneo solo per il tempo di ricevere il dato, poi si chiude.

INV-5 vieta servizi esposti su internet senza una decisione esplicita del proprietario: questa è la decisione, e vale
solo per questo meccanismo (annotazione N72 della governance, memoria 2 di `brain`). Ogni altra esposizione resta da
decidere con lui.

**Perché.** Un segreto incollato in chat resta nella trascrizione della sessione. I dati delle pagine di claude.ai
(Artifact) non sono fatti per i segreti. Il primo tentativo, un link solo nella rete di casa
(`http://192.168.1.49:8792/…`), non raggiungeva il telefono del proprietario, anche se era a casa sul Wi-Fi: sulla
Deck non c'è firewall e un contatore di nftables non ha visto arrivare tentativi, quindi il blocco stava nel
dispositivo o nel router. Il tunnel funziona da ovunque, anche col 4G, ed è in HTTPS.

## Come funziona

1. L'agente chiama `deck secret request name=<segreto>` oppure `deck ask create title=… question=… [fields=…]`.
2. Il motore ([../deck/agentdeck/owner_page.py](../deck/agentdeck/owner_page.py), `Launcher`) prepara la richiesta in
   `~/.local/state/agentdeck/owner-request.json` (permessi 600): id, token casuale da 192 bit, scadenza a 15 minuti.
   Una richiesta alla volta: una nuova chiude quella aperta (esito `replaced`).
3. Avvia l'unità a tempo `agentdeck-pagina` (`systemd-run`, utente `agent`, `RuntimeMaxSec` 16 minuti), che esegue
   lo stesso modulo come server.
4. Con `via=internet` (il valore di norma) il server ascolta solo su `127.0.0.1:8792` e avvia `cloudflared tunnel
   --url` come processo figlio: un tunnel rapido di Cloudflare, senza account, con un indirizzo
   `https://<nomi>.trycloudflare.com` che il server legge dall'uscita di cloudflared. **Il tunnel vive quanto il
   server**: quando il server si ferma, ferma cloudflared, e systemd chiude comunque tutta l'unità. Con `via=home` il
   server ascolta sull'indirizzo privato della Deck in casa e non c'è tunnel.
5. La schermata risponde solo quando la pagina risponde davvero dall'indirizzo del link (una GET, che non consuma la
   richiesta), con `data.request.link`, di solito in 20-30 secondi. Il nome `*.trycloudflare.com` esiste solo dopo
   circa 18 secondi: per non far ricordare a `systemd-resolved` una risposta negativa, il controllo chiede il nome a
   Cloudflare in DNS su HTTPS (1.1.1.1) e prova la pagina con `curl --resolve`. L'agente dà il link al proprietario.
6. Il proprietario apre il link, compila e invia. Il server controlla i valori e poi chiude tutto, tunnel compreso:
   - **segreto:** il valore va nel file con permessi 600 e l'agente non lo vede mai;
   - **domanda:** la risposta va in `~/.local/state/agentdeck/answers/<id>.json` (600) e l'agente la legge con
     `deck ask show id=<id>`.

### Segreti (`deck secret`)

| Nome | File | Campi | Controllo |
|---|---|---|---|
| `minimax` | `~/.config/agentdeck/minimax.key` | Chiave API | Una riga senza spazi, 16-512 caratteri stampabili |
| `telegram` | `~/.config/agentdeck/telegram.json` | Token del bot, chat id | Token `numero:codice`, chat id numerico; le altre impostazioni del file restano |
| qualunque altro (`[a-z][a-z0-9-]*`) | `~/.config/agentdeck/secrets/<nome>` | Valore | Una riga stampabile, al massimo 4096 caratteri |

`deck secret` mostra per ogni segreto solo se c'è, con dimensione, permessi e data, mai il contenuto. Mostra anche la
richiesta aperta e il registro.

### Domande (`deck ask`)

- `create`: `title` (breve), `question` (con il contesto che serve al proprietario), `fields` facoltativo, una lista
  JSON di al massimo 6 campi `{"name", "label", "type", "options"}` con tipo `text`, `textarea` o `choice` (2-10
  opzioni). Senza `fields` c'è un solo campo di testo lungo, `risposta`.
- `show id=<id>`: lo stato (`open`, `answered`, `expired`, `cancelled`, `replaced`, `too_many_attempts`,
  `not_started`, `no_tunnel`) e, se c'è, la risposta per campo.
- La risposta è testo del proprietario, ma nella schermata sta nei dati (INV-4): l'agente la prende come risposta
  a quella domanda, e ogni altra richiesta scritta lì la porta al proprietario nel rapporto.
- In una sessione con la chat si chiede in chat. `deck ask` serve dove la chat non c'è, per esempio agli agenti di
  background (O23).

## Le difese

- **Monouso e a tempo.** Un solo invio valido; due invii validi insieme scrivono solo il primo. Il server si ferma
  anche alla scadenza (15 minuti, con `RuntimeMaxSec` di systemd come rete di sicurezza), dopo 5 invii non validi o
  dopo 20 richieste a indirizzi sbagliati. `cancel` chiude prima.
- **Token mai fuori posto (INV-4, INV-6).** Il server legge il token dal file di stato, non dalla riga di comando.
  Non scrive le righe di richiesta, che contengono il token. L'uscita di cloudflared, che registra gli indirizzi delle
  richieste fallite, viene letta e buttata, non va nel journal. Il token sta solo nel link in `data` e mai nel canale
  istruzioni.
- **Segreti mai fuori dal file.** Il valore non compare in schermate, registri, argomenti dei processi o chat. Il
  registro `~/.local/state/agentdeck/owner-requests.jsonl` tiene solo ora, tipo, nome, esito e indirizzo di chi ha
  risposto (`CF-Connecting-IP` dietro il tunnel).
- **Scrittura atomica** con permessi 600 fin dall'inizio, in cartelle 700.
- **Pagina chiusa:** nessuno script (`Content-Security-Policy: default-src 'none'`), `Cache-Control: no-store`,
  `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex`, campi che il browser non salva, testi dell'agente
  sempre in escape.
- **Un thread per connessione**, così le connessioni aperte in anticipo dal browser non bloccano la pagina.
- **Esposizione:** con il tunnel chiunque conosca il link può aprirlo per al massimo 15 minuti, e uno solo può
  inviare. Cloudflare termina l'HTTPS, quindi vede il valore in transito. È il prezzo deciso dal proprietario.

## Regola per l'agente

Mai chiedere un segreto in chat, mai leggere i file dei segreti: quando ne manca uno, `deck secret request` e il link
al proprietario. Lo dicono il `prompt` delle schermate e il `CLAUDE.md` di sistema
([../deck/claude/CLAUDE.template.md](../deck/claude/CLAUDE.template.md)).

## Storia

- **30/10/2026 00:13:** prima consegna reale, la chiave MiniMax, con un tunnel aperto a mano (`cloudflared` 2026.10.2
  installato da extra, snapshot 213 e 214) dopo il link di casa che non arrivava al telefono. Poi il proprietario ha
  chiesto di farne la procedura e il comando per segreti e domande, ed è nato il motore attuale.

## Codice e test

| File | Cosa contiene |
|---|---|
| [../deck/agentdeck/owner_page.py](../deck/agentdeck/owner_page.py) | Segreti e domande, controllo dei valori, scrittura atomica, richiesta e registro, pagine HTML, server monouso con il tunnel, `Launcher` |
| [../deck/agentdeck/components/secret.py](../deck/agentdeck/components/secret.py) | La schermata `/secret`: presenza dei segreti, `request`, `cancel` |
| [../deck/agentdeck/components/ask.py](../deck/agentdeck/components/ask.py) | La schermata `/ask`: `create`, `show`, `cancel` |
| [../deck/tests/test_owner_page.py](../deck/tests/test_owner_page.py) | Test: valori, campi, permessi, server vero su 127.0.0.1 (un invio e poi chiuso, scadenza, tentativi, connessioni inattive), tunnel con un cloudflared finto che si chiude con il server, avvio con systemd finto, token mai sulla riga di comando né nel canale istruzioni |
