# Segreti del proprietario: la richiesta web monouso (`deck secret`)

Come arrivano sulla Deck i segreti che servono al sistema, la chiave API di MiniMax e il token del bot Telegram,
senza passare dalla chat e senza che l'agente li veda. È nata dalla richiesta del proprietario del 30/10/2026
("inviami una richiesta web e ti mando la chiave"), obiettivo O23, task O23.T1. Indice: [README.md](README.md).

## Perché non la chat

Un segreto incollato in chat resta nella trascrizione della sessione, sulla Deck e nella conversazione. Le pagine
di claude.ai (Artifact) non vanno bene neppure loro: i loro dati condivisi non sono fatti per i segreti. Il valore
deve andare dal browser del proprietario direttamente al file sulla Deck.

## Come funziona

1. L'agente chiama `deck secret request name=minimax` (oppure `name=telegram`).
2. `deck` prepara la richiesta: un token casuale da 192 bit, l'indirizzo privato della Deck nella rete di casa e una
   scadenza di 15 minuti, in `~/.local/state/agentdeck/secret-request.json` (permessi 600). Poi avvia l'unità a tempo
   `agentdeck-segreto` (`systemd-run`, utente `agent`, `RuntimeMaxSec` 16 minuti), che esegue
   [../deck/agentdeck/secret_drop.py](../deck/agentdeck/secret_drop.py).
3. La schermata risponde con il link, `http://<indirizzo di casa>:8792/<token>`, che l'agente passa al proprietario.
4. Il proprietario apre il link da un dispositivo collegato alla rete di casa, incolla il valore e invia.
5. Il server controlla la forma del valore, lo scrive nel file con permessi 600 e si ferma. Il link non vale più.
6. L'agente controlla con `deck secret`: in `data.slots` il segreto risulta presente (dimensione, permessi, data,
   mai il contenuto) e `data.recent` riporta `received`.

| Segreto | File | Campi della pagina | Controllo |
|---|---|---|---|
| `minimax` | `~/.config/agentdeck/minimax.key` | Chiave API | Una riga senza spazi, 16-512 caratteri stampabili |
| `telegram` | `~/.config/agentdeck/telegram.json` | Token del bot, chat id | Token `numero:codice`, chat id numerico; le altre impostazioni del file restano |

## Le difese

- **Solo rete di casa (INV-5).** Il server ascolta solo sull'indirizzo IPv4 privato con cui la Deck esce (oggi
  `192.168.1.49`, su `wlan0`). Se quell'indirizzo non è privato, la richiesta viene rifiutata. Il router non inoltra la
  porta 8792, quindi da fuori casa il link non funziona: in quel caso il proprietario scrive il file via SSH.
- **Monouso e a tempo.** Un solo valore valido, poi il server si ferma. Si ferma anche alla scadenza (15 minuti,
  con `RuntimeMaxSec` di systemd come rete di sicurezza), dopo 5 valori non validi o dopo 20 richieste a indirizzi
  sbagliati. Una richiesta nuova sostituisce quella aperta; `deck secret cancel` la chiude.
- **Il valore non esce dal file (INV-4, INV-6).** Il valore non entra negli argomenti dei processi (il server legge
  il token dal file di stato, non dalla riga di comando), nei registri (il server non scrive le righe di richiesta,
  che contengono il token), nelle schermate di `deck` né nella chat. Il registro
  `~/.local/state/agentdeck/secret-requests.jsonl` tiene solo ora, segreto, esito (`received`, `expired`,
  `too_many_attempts`, `cancelled`, `not_started`) e indirizzo di chi ha risposto.
- **File scritto in modo atomico** con permessi 600 fin dall'inizio, nella cartella `~/.config/agentdeck` con
  permessi 700.
- **Pagina chiusa:** `Content-Security-Policy` senza script, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`,
  campi che non si salvano nel browser.
- **Limite noto:** la pagina viaggia in HTTP semplice dentro la rete di casa. Il Wi-Fi è cifrato con WPA2, ma un
  dispositivo della stessa rete che conosce la password del Wi-Fi potrebbe in teoria leggere il valore in transito.
  HTTPS con un certificato fatto in casa farebbe mostrare un avviso al browser senza proteggere di più chi non
  controlla l'impronta del certificato.

## Regola per l'agente

Mai chiedere un segreto in chat e mai leggere i file dei segreti: quando ne manca uno, `deck secret request` e il
link al proprietario. Lo dice il `prompt` della schermata e il `CLAUDE.md` di sistema
([../deck/claude/CLAUDE.template.md](../deck/claude/CLAUDE.template.md)).

## Codice e test

| File | Cosa contiene |
|---|---|
| [../deck/agentdeck/secret_drop.py](../deck/agentdeck/secret_drop.py) | Segreti conosciuti, controllo dei valori, scrittura atomica, richiesta e registro, indirizzo di casa, server monouso |
| [../deck/agentdeck/components/secret.py](../deck/agentdeck/components/secret.py) | La schermata `/secret`: presenza dei segreti, `request` con l'unità a tempo, `cancel` |
| [../deck/tests/test_secret.py](../deck/tests/test_secret.py) | Test: valori, permessi, solo indirizzi privati, server vero su 127.0.0.1 (un valore e poi chiuso, scadenza, tentativi), schermata con systemd finto, token mai nel canale istruzioni né sulla riga di comando |
