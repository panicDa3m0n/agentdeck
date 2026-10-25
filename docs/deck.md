# deck: il motore

`deck` è l'interfaccia di sistema di AgentDeck per gli agenti: implementa il protocollo descritto in
[protocollo.md](protocollo.md). Qui ci sono il codice, l'installazione e il modo di aggiungere componenti.
Indice: [README.md](README.md).

## Uso

```bash
ssh agentdeck deck                 # schermata principale: i componenti
ssh agentdeck deck protocol        # le regole del protocollo, descritte dal sistema stesso
ssh agentdeck 'deck --pretty'      # JSON indentato, per leggerlo a occhio
```

Ogni chiamata restituisce una schermata JSON e il codice di uscita `1` solo se la schermata è un errore.
Sulla Deck una chiamata dura circa 0,09 secondi (Python 3.14, misura del 25/10/2026).

## Componenti attivi

| Indirizzo | Modulo | Contenuto |
|---|---|---|
| `/` | [../deck/agentdeck/components/home.py](../deck/agentdeck/components/home.py) | Schermata principale: host, versione, tempo di attività, componenti |
| `/protocol` | [../deck/agentdeck/components/protocol_info.py](../deck/agentdeck/components/protocol_info.py) | Il protocollo descritto all'agente: campi, stati, effetti, codici d'errore, canale istruzioni |
| `/status` | [../deck/agentdeck/components/status.py](../deck/agentdeck/components/status.py) | Stato della macchina (vedi sotto) |

In arrivo con l'obiettivo O3: `/snapshot` (snapshot e rollback).

### `/status`: stato della macchina

L'equivalente di Monitor Attività e Informazioni di sistema. Le letture stanno in
[../deck/agentdeck/system.py](../deck/agentdeck/system.py): una lettura che fallisce vale `null` e compare in
`data.read_errors`, senza rompere la schermata. Risponde in circa 0,27 secondi.

| Sezione di `data` | Contenuto | Fonte |
|---|---|---|
| `system` | Nome, sistema operativo, kernel, tempo di attività | `/etc/os-release`, `uname`, `/proc/uptime` |
| `hardware` | Produttore, modello, BIOS, CPU | `/sys/class/dmi/id`, `/proc/cpuinfo` |
| `load` | Carico medio a 1, 5, 15 minuti | `/proc/loadavg` |
| `battery` | Percentuale, stato, alimentatore | `/sys/class/power_supply` |
| `sensors` | Temperature di APU, GPU, NVMe, ACPI; giri ventola | `/sys/class/hwmon` |
| `memory_bytes` | RAM totale, usata, disponibile; zram | `/proc/meminfo` |
| `disk_bytes` | Spazio della radice | `statvfs("/")` |
| `network` | Interfacce, gateway, Wi-Fi (SSID, frequenza, banda, segnale, velocità) | `ip -j`, `iw dev <if> link` |
| `listening` | Porte in ascolto con il processo | `sudo ss -Hltunp` |
| `services` | Stato del sistema, servizi falliti | `systemctl --output=json` |
| `snapshots` | Numero, ultimo, ultimo manuale | `sudo snapper --jsonout list` |
| `time` | Sincronizzazione NTP, fuso | `timedatectl show` |

| Avviso | Livello | Quando |
|---|---|---|
| `SERVICES_FAILED` | critical | Almeno un servizio fallito |
| `TEMP_HIGH` | warning / critical | APU ≥ 85 °C / ≥ 95 °C |
| `DISK_LOW`, `MEMORY_LOW` | warning | Meno del 10% libero |
| `BATTERY_LOW` | warning / critical | A batteria sotto il 20% / 10% |
| `WIFI_BAND_2G` | warning | Wi-Fi sulla banda a 2,4 GHz |
| `WIFI_SIGNAL_WEAK` | warning | Segnale sotto -75 dBm |
| `TIME_NOT_SYNCED` | warning | Orologio non sincronizzato |
| `LLMNR_LISTENING` | info | LLMNR in ascolto sulla LAN (superfluo: si usa mDNS) |
| `FAN_UNREADABLE` | info | Giri della ventola non leggibili (la gestisce il firmware) |
| `READ_FAILED` | warning | Una sezione non è stata letta |

SSID, nomi dei servizi e descrizioni degli snapshot sono testo esterno: stanno solo nei dati (INV-4).
Gli avvisi oggi non hanno un'azione collegata: servirà un componente di rete.

## Codice

| File | Ruolo |
|---|---|
| [../deck/deck](../deck/deck) | Comando eseguibile: avvia la riga di comando |
| [../deck/agentdeck/cli.py](../deck/agentdeck/cli.py) | Legge la chiamata, aggiunge `meta`, valida la schermata, stampa il JSON, imposta l'uscita |
| [../deck/agentdeck/engine.py](../deck/agentdeck/engine.py) | Motore: indirizzi, componenti, validazione dei parametri, conferme, schermate di errore |
| [../deck/agentdeck/protocol.py](../deck/agentdeck/protocol.py) | Costruzione e validazione delle schermate; `SysText` e `sys_text()` per il canale istruzioni |
| [../deck/agentdeck/confirm.py](../deck/agentdeck/confirm.py) | Codici di conferma: una azione, quei parametri, 5 minuti, una volta sola |
| [../deck/agentdeck/components/](../deck/agentdeck/components/__init__.py) | Un modulo per componente; l'elenco dei componenti attivi è in `__init__.py` |
| [../deck/agentdeck/system.py](../deck/agentdeck/system.py) | Letture dello stato della Deck da `/proc`, `/sys` e comandi; parser puri |
| [../deck/tests/test_deck.py](../deck/tests/test_deck.py) | Test di conformità, iniezione, parametri, conferme, guasti |
| [../deck/tests/test_status.py](../deck/tests/test_status.py) | Test di `/status`: parser su output reali, avvisi, nomi esterni nei soli dati |
| [../deck/tests/live_status_check.py](../deck/tests/live_status_check.py) | Controllo dal vivo sulla Deck: ogni valore di `deck status` contro una lettura indipendente |
| [../deck/install.sh](../deck/install.sh) | Installazione e aggiornamento sulla Deck, schermo compreso |
| [../deck/screen/](../deck/screen/agentdeck_screen.py) | Schermo della Deck: registrazione dei comandi, visualizzatore, servizio ([schermo.md](schermo.md)) |
| [../deck/tests/test_screen.py](../deck/tests/test_screen.py) | Test dello schermo: pulizia del testo, segreti oscurati, esiti di `deck` |

Solo libreria standard di Python, compatibile da Python 3.10 (Mac) in su (Deck: 3.14).

## Sicurezza del canale istruzioni nel codice

- I campi del canale istruzioni (`title`, `prompt`, etichette, motivi, messaggi, descrizioni dei parametri)
  accettano solo `SysText`. Una stringa normale in quei campi solleva `UnsafeText`: l'errore si vede subito
  durante lo sviluppo, non arriva mai all'agente.
- `sys_text(modello, **valori)` riempie un modello scritto nel codice e accetta come valori solo numeri o
  identificatori senza spazi. Testo libero, come descrizioni, nomi di file, log o SSID, va in `data`.
- Ogni chiamata viene validata contro il protocollo prima di essere stampata: una schermata non conforme
  diventa un errore `FAILED`, con i problemi elencati nei dati.

## Installazione e aggiornamento

```bash
deck/install.sh
```

Lo script, ripetibile:

1. lancia i test sul Mac;
2. si assicura che `python` sia installato sulla Deck (con pacman, quindi con gli snapshot di snap-pac);
3. copia `deck/` in `/opt/agentdeck` (proprietario `agent`, così l'agente può correggerlo sul posto) insieme
   al file `VERSION`;
4. collega `/usr/local/bin/deck` a `/opt/agentdeck/deck`;
5. lancia i test sulla Deck e prova `deck` e un indirizzo inesistente.

Dopo modifiche a `/status`, il controllo dal vivo confronta ogni valore con gli strumenti classici:

```bash
ssh agentdeck python /opt/agentdeck/tests/live_status_check.py
```

I codici di conferma in sospeso stanno in `~/.local/state/agentdeck/confirm.json` dell'utente `agent`.

## Aggiungere un componente

1. Creare un modulo in `deck/agentdeck/components/` con una classe che estende `Component`
   ([engine.py](../deck/agentdeck/engine.py)):
   - `path`: l'indirizzo, per esempio `"/status"`;
   - `title` e `summary`: come appare tra i figli della schermata principale (`SysText`);
   - `view(ctx)`: la schermata in stato `ok`, costruita con `screen()`;
   - `actions(ctx)`: le azioni possibili ora, costruite con `action()` e `param()`;
   - `run(ctx, azione, parametri)`: esegue un'azione già validata e restituisce la schermata `done`;
   - `preview(ctx, azione, parametri)`: solo per le azioni distruttive, restituisce un `Preview` con
     cambiamenti, cose intatte, come tornare indietro, riavvio, e il prompt che riceve il codice di conferma.
2. Aggiungerlo all'elenco in `components/__init__.py`.
3. Scrivere i test: almeno una chiamata per schermata e per azione, validate contro il protocollo e
   controllate per l'assenza di testo esterno nel canale istruzioni (come fa `DeckTests.call`).
4. Documentarlo qui, nella tabella dei componenti, e in un documento suo se serve (INV-9).
