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

## Server MCP (O10.T6)

`deck mcp` serve le stesse schermate come server MCP su stdio, in JSON-RPC 2.0 con un messaggio per riga. Così
Claude Code usa `deck` come strumento nativo, con i parametri tipizzati, invece di comporre comandi Bash
(proposta A6.2 di [architettura.md](architettura.md)). Codice: [../deck/agentdeck/mcp.py](../deck/agentdeck/mcp.py);
`mcp` è una parola riservata della riga di comando, non un indirizzo.

| Cosa offre | Come |
|---|---|
| Strumento `open` | Apre qualunque schermata; `path` è uno degli indirizzi dei componenti |
| Uno strumento per azione | `<componente>_<azione>`, per esempio `snapshot_create`, `service_restart`, `term_start`; lo schema degli argomenti nasce dalla specifica dei parametri (`int` diventa `integer`, `enum` un elenco chiuso, `max_length` diventa `maxLength`) |
| Annotazioni | `readOnlyHint` per le azioni `read`, `destructiveHint` per le `destructive` |
| Risorse | Ogni schermata è anche una risorsa `deck:<indirizzo>`, per esempio `deck:/status` |
| Istruzioni del server | Testo del sistema, consegnato all'avvio: dati e istruzioni separati, partire da `/status`, conferme in due passi |

- **Il risultato di ogni strumento è la schermata del motore**, prodotta da `cli.render` come per la riga di
  comando. Anteprime, codici di conferma, errori e convalida restano identici.
- **Le azioni distruttive restano in due passi.** Lo strumento ha un argomento `confirm` facoltativo: senza
  quello non cambia nulla e restituisce l'anteprima con `confirm.token`; con lo stesso codice e gli stessi
  argomenti esegue. Una schermata di errore arriva come risultato con `isError: true`.
- **INV-4.** Nomi, titoli e descrizioni degli strumenti nascono solo dalle etichette `SysText` dei componenti e
  da modelli scritti in `mcp.py`. Il testo esterno resta nei dati della schermata.
- **Flusso pulito.** Durante il servizio, `print` finisce su stderr, così niente di estraneo si mescola al
  JSON-RPC. Ogni chiamata va sullo schermo della Deck come quelle di `deck`. `ssh-log.sh` non copia il flusso
  di `deck mcp` nel journal ([schermo.md](schermo.md)).
- **Versioni del protocollo MCP accettate:** 2025-11-25, 2025-06-18, 2025-03-26, 2024-11-05. A un client che ne
  chiede un'altra risponde con 2025-06-18.

Dove è registrato:
- **sulla Deck**, per l'utente `agent`: `claude mcp add --transport stdio --scope user deck --
  /usr/local/bin/deck mcp`, eseguito da [../deck/claude/install.sh](../deck/claude/install.sh). Le
  impostazioni gestite permettono tutti gli strumenti `mcp__deck` ([claude-code.md](claude-code.md));
- **sul Mac**, per le sessioni in questo repository: [../.mcp.json](../.mcp.json) avvia `ssh agentdeck deck mcp`.
  Claude Code chiede di approvarlo alla prima apertura.

Verifiche del 26/10/2026:
- dal Mac, con un client JSON-RPC via SSH: inizializzazione, 19 strumenti, `open /status`, `service_show`,
  errore `NOT_FOUND` come risultato di errore, lettura di una risorsa, tutto in 1,7 secondi;
- da una sessione di Claude Code sulla Deck (`claude -p`): server collegato, 19 strumenti; la sessione ha aperto
  `/status` e chiesto l'anteprima di un rollback con `snapshot_rollback` senza confermarla, nessun permesso
  negato.

## Componenti attivi

| Indirizzo | Modulo | Contenuto |
|---|---|---|
| `/` | [../deck/agentdeck/components/home.py](../deck/agentdeck/components/home.py) | Schermata principale: host, versione, tempo di attività, componenti |
| `/protocol` | [../deck/agentdeck/components/protocol_info.py](../deck/agentdeck/components/protocol_info.py) | Il protocollo descritto all'agente: campi, stati, effetti, codici d'errore, canale istruzioni |
| `/status` | [../deck/agentdeck/components/status.py](../deck/agentdeck/components/status.py) | Stato della macchina (vedi sotto) |
| `/snapshot` | [../deck/agentdeck/components/snapshot.py](../deck/agentdeck/components/snapshot.py) | Snapshot del sistema: elenco, creazione, rollback (vedi sotto) |
| `/network` | [../deck/agentdeck/components/network.py](../deck/agentdeck/components/network.py) | Rete: interfacce, Wi-Fi e reti visibili, risoluzione dei nomi, porte (vedi sotto) |
| `/service` | [../deck/agentdeck/components/service.py](../deck/agentdeck/components/service.py) | Servizi di systemd: elenco, dettaglio, start, stop, restart, enable, disable (vedi sotto) |
| `/logs` | [../deck/agentdeck/components/logs.py](../deck/agentdeck/components/logs.py) | Journal di systemd: righe per unità, periodo e gravità (vedi sotto) |
| `/update` | [../deck/agentdeck/components/update.py](../deck/agentdeck/components/update.py) | Aggiornamenti del sistema: controllo, applicazione con snapshot e verifica, riavvio (vedi sotto) |
| `/obligations` | [../deck/agentdeck/components/obligations.py](../deck/agentdeck/components/obligations.py) | Obblighi del sistema verso l'agente: aperti, chiusi, done e dismiss; nascono dall'hook di pacman ([obblighi.md](obblighi.md)) |
| `/term` | [../deck/agentdeck/components/term.py](../deck/agentdeck/components/term.py) | Adattatore dei programmi interattivi: un programma in tmux come schermata, domande riconosciute, profili scritti dall'agente ([adattatore.md](adattatore.md)) |

### `/network`: rete

- `deck network` risponde in circa 0,08 secondi. Le reti visibili vengono dalla **cache di scansione del
  kernel**, che tiene solo gli access point visti di recente.
- `deck network scan` (effetto `read`) fa una **scansione fresca**: dura circa 5 secondi.

| Sezione di `data` | Contenuto | Fonte |
|---|---|---|
| `interfaces`, `default_gateway` | Interfacce con stato e IPv4, gateway | `ip -j` |
| `wifi` | Collegamento: BSSID, SSID, frequenza, banda, segnale, velocità | `iw dev wlan0 link` |
| `networks` | Reti visibili per nome, con bande, segnale migliore per banda e access point | `iw dev wlan0 scan [dump]` |
| `connected_network` | La rete collegata, le bande su cui la si vede, le **reti sorelle** | calcolato |
| `name_resolution` | Server DNS, mDNS e LLMNR, globali e per interfaccia | `resolvectl status --json=short` |
| `listening` | Porte in ascolto | `sudo ss -Hltunp` |

Le **reti sorelle** sono altre reti dello stesso router. Le si riconosce da un BSSID che differisce solo nel
primo o nell'ultimo byte (`same_router_bssid`), oppure da un nome che inizia come quello della rete collegata
(`ssid_prefix`). Sulla rete di casa i 5 GHz sono una rete distinta, "… - 5Ghz": vedi
[hardware.md](hardware.md).

| Avviso | Livello | Azione collegata |
|---|---|---|
| `WIFI_BAND_2G` | warning | `prefer_5ghz` se si vedono i 5 GHz della stessa rete o di una rete sorella, altrimenti `scan` |
| `LLMNR_LISTENING` | info | `llmnr_off` |

`deck status` usa gli stessi codici e rimanda a `/network`. SSID e nomi di rete sono testo esterno: stanno
solo nei dati (INV-4), anche nelle anteprime (`data.target`, `data.fallback`).

#### Azioni che cambiano la rete

| Azione | Effetto | Disponibile quando | Cosa fa |
|---|---|---|---|
| `llmnr_off` | destructive | LLMNR è acceso | Snapshot, drop-in `/etc/systemd/resolved.conf.d/20-agentdeck-llmnr.conf` con `LLMNR=no`, riavvio di resolved |
| `llmnr_on` | safe | LLMNR è spento | Toglie il drop-in e riavvia resolved: è l'annullamento di `llmnr_off` |
| `prefer_5ghz` | destructive | Wi-Fi a 2,4 GHz, una rete a 5 GHz dello stesso router nella scansione, nessun cambio in corso | Snapshot, poi il cambio di rete con ritorno automatico (sotto) |
| `keep_5ghz` | safe | Un cambio aspetta la conferma | Conferma che la Deck è raggiungibile sulla nuova rete |

Dopo `llmnr_off` e `llmnr_on` `deck` verifica subito, per al massimo 5 secondi: stato di LLMNR (porta 5355
e impostazione globale), mDNS sull'interfaccia di default, una query DNS. Se la verifica non passa rimette
l'impostazione precedente e risponde `FAILED`.

Il **cambio Wi-Fi** gira come root nell'unità transitoria `agentdeck-wifi-switch`
([../deck/agentdeck/wifi_switch.py](../deck/agentdeck/wifi_switch.py)), staccata dalla sessione SSH che il
cambio interrompe:

1. se la rete di destinazione non ha un profilo iwd, lo crea copiando solo la `Passphrase` dal profilo della
   rete attuale. Le chiavi SAE-PT dipendono dal nome della rete e non si copiano; la password non viene mai
   stampata. Se il profilo attuale non ha una password, l'anteprima risponde `NOT_AVAILABLE`;
2. si collega alla destinazione e aspetta fino a 60 secondi l'SSID giusto, un IPv4 e il gateway che risponde
   al ping;
3. scrive lo stato `awaiting_confirmation` e aspetta fino a 3 minuti `deck network keep_5ghz`, che crea
   `/run/agentdeck/wifi-keep`;
4. con la conferma scrive `/etc/iwd/main.conf` con `[Rank] BandModifier5GHz=1.5` (iwd preferisce i 5 GHz);
   senza conferma, senza indirizzo o per qualunque errore torna alla rete di prima e toglie il profilo
   creato. Se il ritorno non dà un indirizzo riavvia iwd, che si ricollega da solo a una rete nota.

Lo stato di ogni passo sta in `/var/lib/agentdeck/wifi-switch.json` e compare in `data.wifi_switch`:
`switching`, `awaiting_confirmation`, `kept`, `reverted` (con `reason`), `failed`. Un cambio "in corso" la
cui unità non è più attiva (riavvio, errore) vale `interrupted`.

| Avviso | Livello | Quando |
|---|---|---|
| `WIFI_SWITCH_PENDING` | critical | Un cambio aspetta `keep_5ghz`: senza conferma la Deck torna indietro |
| `WIFI_SWITCH_REVERTED` | warning | L'ultimo cambio non si è concluso (`reverted`, `failed`, `interrupted`) |

Sequenza per l'agente: `deck network scan`, poi `deck network prefer_5ghz` per l'anteprima, poi la conferma.
Dopo circa 20 secondi ci si ricollega con `ssh agentdeck` (se l'IP è cambiato:
`dns-sd -G v4 agentdeck.local` dal Mac), si controlla `deck network` e si conferma con
`deck network keep_5ghz`.

Il controllo dal vivo confronta ogni valore con `ip`, `iw`, `resolvectl` e `ss`:

```bash
ssh agentdeck python /opt/agentdeck/tests/live_network_check.py
```

### `/service`: servizi di systemd

- `deck service` elenca tutti i servizi caricati, come `systemctl list-units --type=service --all`, con
  `enabled` letto dal file dell'unità (`null` se systemd non lo riporta). In `data` ci sono anche i conteggi, i
  servizi falliti e quelli protetti. Risponde in circa 0,5-0,8 secondi; la schermata pesa circa 23 KB.
- `deck service show name=<unità>` (effetto `read`) mostra le proprietà di un servizio come `systemctl show`:
  stato, abilitazione, PID, memoria, avvio, file dell'unità, dipendenze. Il suffisso `.service` si può omettere
  e gli alias si risolvono (`dbus` diventa `dbus-broker.service`). Si gestiscono solo unità `.service`.

| Azione | Effetto | Snapshot prima | Note |
|---|---|---|---|
| `start` | safe | no | Rifiutata se il servizio è mascherato |
| `stop` | destructive | no | Torna da solo al riavvio se è abilitato |
| `restart` | destructive | no | Per i servizi di rete l'anteprima avverte che SSH può cadere per qualche secondo |
| `enable` | safe | sì | Solo all'avvio (niente `--now`); rifiutata per unità `static`, `indirect` e mascherate |
| `disable` | destructive | sì | Il servizio resta attivo fino a uno `stop` |

Dopo ogni azione `deck` rilegge il servizio, aspettando fino a 10 secondi che finisca di avviarsi o fermarsi,
e risponde `FAILED` se non ha raggiunto lo stato atteso o se `systemctl` ha dato errore. Il messaggio di
`systemctl` sta in `data.systemctl_error`.

**Protezione dell'accesso (INV-1).** Sono protetti i servizi da cui dipende l'accesso dell'agente:
`sshd`, `systemd-networkd`, `iwd`, `systemd-resolved` e `dbus-broker`, il bus di sistema senza cui iwd perde la
rete (`system.ACCESS_SERVICES`). A questi si aggiungono le loro dipendenze dirette che sono servizi
(`Requires`, `Requisite`, `BindsTo`), lette dal vivo; oggi non ce ne sono altre.
- `stop` e `disable` di un servizio protetto, o di un servizio richiesto da uno protetto, sono rifiutati con
  `NOT_AVAILABLE` e il motivo.
- `restart` di `dbus-broker` è rifiutato; `restart` di `sshd` è ammesso solo se la configurazione passa
  `sshd -t`.

| Avviso | Livello | Azione collegata |
|---|---|---|
| `SERVICES_FAILED` | critical | `show` su `/service`; lo stesso codice in `deck status` rimanda a `/service` |

Nomi, descrizioni e messaggi di `systemctl` sono testo esterno: stanno solo nei dati (INV-4).

Il controllo dal vivo confronta l'elenco con `systemctl` e fa il giro completo delle azioni su un servizio di
prova, `agentdeck-test`, che crea e poi toglie. Controlla anche i rifiuti sui servizi protetti:

```bash
ssh agentdeck python /opt/agentdeck/tests/live_service_check.py
```

### `/logs`: il journal

- `deck logs` mostra avvisi ed errori dell'avvio in corso: le ultime 50 righe con gravità `warning` o più grave.
  Risponde in circa 20 ms.
- `deck logs query` (effetto `read`) filtra con questi parametri, tutti facoltativi:

| Parametro | Forme accettate | Opzione di journalctl |
|---|---|---|
| `unit` | `sshd`, `sshd.service`, `snapper-timeline.timer`, `session-5.scope`… (`.service` se manca il tipo) | `-u` |
| `since` | `30m`, `2h`, `7d` (fa), `today`, `yesterday`, `boot` (avvio in corso), `YYYY-MM-DD[ HH:MM[:SS]]` | `--since`, oppure `-b` |
| `until` | come `since`, tranne `boot` | `--until` |
| `priority` | `emerg`, `alert`, `crit`, `err`, `warning`, `notice`, `info`, `debug`: quella e le più gravi | `-p` |
| `lines` | da 1 a 1000, predefinito 100: le più recenti | `-n` |
| `include_agent` | `true` per includere la traccia dei comandi dell'agente (predefinito `false`) | — |

Ogni riga di `data.entries`, dalla più vecchia, ha:
- `time` (ISO, millisecondi), `priority` (0-7) e `level`;
- `unit` (l'unità del processo) e `subject_unit` (l'unità di cui parla un messaggio di systemd);
- `identifier`, `pid`, `message`, `cursor`.

`data.journalctl` riporta la riga di comando equivalente, mentre `data.truncated` dice se ci sono righe più
vecchie oltre `lines`.

**La traccia dell'agente.** Lo schermo della Deck scrive nel journal ogni comando dell'agente e la sua
risposta, con gli identificatori `agentdeck-cmd`, `agentdeck-out` e `agentdeck-err` ([schermo.md](schermo.md)).
Senza escluderli, ogni risposta di `deck logs` tornerebbe nelle interrogazioni successive.
- `deck` toglie quelle righe da sé, perché in systemd 262 `journalctl -T` non filtra con `-o json` (trappola P14).
  Chiede a journalctl più righe finché, dopo il filtro, ne restano `lines`, fino a un massimo di 20.000.
- Con `include_agent=true` la traccia resta.

Il testo dei log è scritto da programmi e utenti qualsiasi (basta `logger`): sta solo nei dati (INV-4).
`deck service show` porta ai log del servizio con `data.logs` (`deck logs query unit=<unità>`).

Il controllo dal vivo confronta cinque filtri con una lettura indipendente di `journalctl -o json` e scrive
una riga malevola con `logger` per verificare che resti nei dati:

```bash
ssh agentdeck python /opt/agentdeck/tests/live_logs_check.py
```

### `/update`: aggiornamenti del sistema

| Azione | Effetto | Cosa fa |
|---|---|---|
| (schermata) | — | L'ultimo controllo salvato, con l'età (`data.checked`, `data.age_s`); stato del kernel; ultimo aggiornamento |
| `check` | read | Gli aggiornamenti disponibili, come `checkupdates`: sincronizza una copia del database dei pacchetti in `/tmp/agentdeck-checkupdates`, quello del sistema non cambia. Circa 1,5 secondi |
| `apply` | destructive | Anteprima con i pacchetti e cosa comportano, poi l'aggiornamento (sotto) |
| `verify` | read | Servizi dell'accesso attivi, `sshd -t`, DNS, servizi falliti, file `.pacnew`, moduli del kernel in uso |
| `reboot` | destructive | Riavvio dopo 10 secondi, disponibile quando un aggiornamento lo aspetta |

`data.summary` dice cosa comporta un insieme di aggiornamenti
([../deck/agentdeck/system.py](../deck/agentdeck/system.py), `classify_updates`):
- **riavvio** per kernel (`linux`, `linux-lts`), firmware (`linux-firmware*`), `amd-ucode`, `systemd`, `glibc` e
  `dbus-broker`;
- **GRUB** quando si aggiorna `grub`;
- **accesso** per `openssh`, `iwd`, `systemd`, `dbus-broker`, `openssl`, `pam` e `glibc`.

**Applicazione.**
1. Nuovo controllo: l'anteprima e l'applicazione partono dallo stato del mirror in quel momento.
2. Snapshot prima (`agentdeck: prima di update`); se non si crea, non cambia niente.
3. `pacman -Syu --noconfirm` nell'unità transitoria `agentdeck-update`, con l'output in
   `/var/log/agentdeck/update.log`: se SSH cade l'aggiornamento continua, perché non scrive in una pipe legata
   alla sessione. Gli snapshot pre e post di snap-pac si aggiungono come sempre.
4. Se `grub` è stato aggiornato: `grub-install` nell'EFI (voce GRUB e percorso di riserva), poi
   `grub-mkconfig`, con gli stessi comandi di [../install/install.sh](../install/install.sh). Binario e moduli
   restano coerenti; un test controlla che i comandi coincidano con l'installatore.
5. Snapshot dopo (`agentdeck: dopo update`).
6. Verifica. Bloccano l'esito un servizio dell'accesso fermo, `sshd -t` che fallisce, il DNS che non risponde e
   servizi falliti nuovi; sono solo segnalati il riavvio necessario e i file `.pacnew`.

Se pacman, GRUB o la verifica falliscono, la risposta è `FAILED`, con il risultato, i problemi e le ultime 60
righe di pacman nei dati. Indica il rollback allo snapshot di prima e dice di non riavviare.

**Limite con GRUB.** `/boot`, con i moduli di GRUB, sta negli snapshot; l'EFI no. Dopo un aggiornamento di
`grub`, `deck snapshot rollback` rifiuta gli snapshot di prima perché hanno un GRUB diverso: resta solo lo
snapshot dopo. L'anteprima lo dice.

Dopo un aggiornamento che chiede il riavvio compare l'avviso `REBOOT_REQUIRED`, che punta a `reboot`. L'avviso
resta finché il kernel in uso non ha più i moduli installati o finché la Deck non si è riavviata dopo
l'aggiornamento. Poi `deck update verify` conferma lo stato.

| Avviso | Livello | Azione collegata |
|---|---|---|
| `UPDATES_UNCHECKED` | info | `check`, se l'ultimo controllo ha più di 24 ore |
| `UPDATES_AVAILABLE` | info | `apply` |
| `REBOOT_REQUIRED` | warning | `reboot` |

Il controllo salvato e l'ultimo aggiornamento stanno in `~/.local/state/agentdeck/` (`updates.json`,
`last-update.json`) dell'utente `agent`. Nomi, versioni e output di pacman sono testo esterno: stanno solo nei
dati (INV-4).

### `/snapshot`: snapshot del sistema

L'equivalente di Time Machine, sopra Snapper e grub-btrfs.

- `deck snapshot` elenca gli snapshot dal più vecchio al più nuovo, come `snapper list`. Per ognuno indica:
  - `id`, `type` (`single`, oppure `pre`/`post` per le coppie create da pacman), `pre_id`;
  - `date`, `description`, `cleanup` (`timeline` per quelli orari, `number` per quelli di pacman);
  - `userdata` (`source: deck` per quelli creati da `deck`);
  - `in_grub`: vero se è avviabile dal menu snapshot di GRUB, `null` se il menu in quel momento non è
    leggibile.
- `deck snapshot create description="…"` crea uno snapshot singolo (descrizione obbligatoria, massimo 100
  caratteri) e restituisce `done` con il suo `id`. grub-btrfsd lo aggiunge al menu di GRUB in pochi secondi.
- `deck snapshot rollback id=N` riporta il sistema allo snapshot `N`, in due chiamate (protocollo, sezione 7).

| Avviso | Livello | Quando |
|---|---|---|
| `SNAPSHOT_NOT_IN_GRUB` | info | Uno o più snapshot non sono ancora nel menu di GRUB (`data.not_in_grub`) |
| `GRUB_MENU_UNREADABLE` | info | Il menu non è leggibile: grub-btrfsd lo sta riscrivendo, riprovare tra pochi secondi |

Le descrizioni sono testo esterno: stanno solo nei dati (INV-4).

### Rollback

1. **Anteprima** (`deck snapshot rollback id=N`): `status: confirm` con codice valido 5 minuti. Contiene:
   - lo snapshot di destinazione;
   - i pacchetti che verrebbero rimossi, che tornerebbero e che cambierebbero versione (`data.packages`);
   - il controllo dell'accesso (`data.access_check`).

   Niente viene ancora modificato.
2. **Rifiuti di sicurezza** (`NOT_AVAILABLE`), controllati sia nell'anteprima sia all'esecuzione:
   - se nello snapshot mancano sshd o networkd o iwd abilitati, il profilo Wi-Fi, l'utente `agent`, il
     suo sudo, o se `AllowUsers` esclude `agent`: tornarci lascerebbe la Deck senza accesso (INV-1);
   - se lo snapshot ha una versione di GRUB diversa da quella installata: i moduli in `/boot/grub`
     potrebbero non combaciare con GRUB nella partizione EFI e la Deck non si avvierebbe.
3. **Esecuzione** (`… confirm=<codice>`):
   1. salva lo stato attuale come nuovo snapshot (lo `undo_snapshot_id` della risposta);
   2. monta il livello superiore di Btrfs in `/run/agentdeck/btrfs-top`;
   3. crea una copia scrivibile dello snapshot;
   4. rinomina `@` in `@old-<data>` e la copia in `@`. Se il secondo passo fallisce, rimette subito `@` al
      suo posto: il sistema resta com'era e la risposta è `FAILED`;
   5. programma il riavvio dopo 10 secondi.

   GRUB e `fstab` trovano il sistema per nome (`subvol=@`), quindi al riavvio parte lo snapshot.
4. **Dopo il riavvio:** la Deck torna in circa un minuto. `deck status` conferma lo stato.
   - **Annullare** il rollback: `deck snapshot rollback id=<undo_snapshot_id>`.
   - **Cosa non cambia:** `/home`, `/var/log`, la cache dei pacchetti, gli snapshot e la partizione EFI.
   - **Se `deck` è cambiato** dopo lo snapshot di destinazione: `deck` torna alla sua versione di allora,
     quindi va reinstallato con `deck/install.sh`.

Prova reale del 25/10/2026:
- prima è stato creato lo snapshot 15, poi un file segnaposto e il pacchetto `tree`;
- l'anteprima annunciava la rimozione di `tree`;
- dopo la conferma lo stato è stato salvato come snapshot 18 e la Deck è tornata in 44 secondi;
- segnaposto e `tree` erano spariti, e lo snapshot 18 conteneva ancora il segnaposto.

**Pulizia del vecchio sistema:** `@old-<data>` resta sul disco. Occupa solo i blocchi diversi dallo
snapshot, perché Btrfs li condivide. Contiene i subvolumi annidati di systemd (`var/lib/portables`,
`var/lib/machines`), che vanno cancellati prima di lui:

```bash
sudo mount -o subvolid=5 /dev/nvme0n1p2 /mnt
sudo btrfs subvolume delete /mnt/@old-<data>/var/lib/portables /mnt/@old-<data>/var/lib/machines /mnt/@old-<data>
sudo umount /mnt
```

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
Gli avvisi di rete (`WIFI_BAND_2G`, `LLMNR_LISTENING`) rimandano alle azioni di `/network`; gli altri non
hanno ancora un'azione collegata.

## Codice

| File | Ruolo |
|---|---|
| [../deck/deck](../deck/deck) | Comando eseguibile: avvia la riga di comando |
| [../deck/agentdeck/cli.py](../deck/agentdeck/cli.py) | Legge la chiamata, aggiunge `meta`, valida la schermata, stampa il JSON, imposta l'uscita |
| [../deck/agentdeck/engine.py](../deck/agentdeck/engine.py) | Motore: indirizzi, componenti, validazione dei parametri, conferme, schermate di errore |
| [../deck/agentdeck/protocol.py](../deck/agentdeck/protocol.py) | Costruzione e validazione delle schermate; `SysText` e `sys_text()` per il canale istruzioni |
| [../deck/agentdeck/confirm.py](../deck/agentdeck/confirm.py) | Codici di conferma: una azione, quei parametri, 5 minuti, una volta sola |
| [../deck/agentdeck/mcp.py](../deck/agentdeck/mcp.py) | Server MCP: strumenti dalle azioni, risorse, JSON-RPC su stdio (`deck mcp`) |
| [../deck/agentdeck/term.py](../deck/agentdeck/term.py) | Adattatore: tmux, stato del processo e del terminale, riconoscimento delle domande, profili, sessioni |
| [../deck/agentdeck/obligations.py](../deck/agentdeck/obligations.py) | Obblighi: modelli dei messaggi, archivio, nascita dopo un'installazione, chiusura da sé, campo `obligations` di ogni schermata |
| [../deck/system/](../deck/system/95-agentdeck-obligations.hook) | Hook di pacman che apre gli obblighi dopo le installazioni, con il suo script |
| [../deck/agentdeck/access.py](../deck/agentdeck/access.py) | Regole che proteggono l'accesso (INV-1), usate dalla guardia di Claude Code e da `deck term` |
| [../deck/profiles/](../deck/profiles/pacman.json) | Profili dell'adattatore forniti con `deck` |
| [../deck/tests/test_mcp.py](../deck/tests/test_mcp.py) | Test del server MCP: strumenti e schemi, conferme in due passi, errori, risorse, flusso stdio, INV-4 |
| [../deck/tests/test_term.py](../deck/tests/test_term.py) | Test dell'adattatore: riconoscimento, profili, sessioni con tmux finto, segreti, guardia dell'accesso, INV-4 |
| [../deck/tests/test_obligations.py](../deck/tests/test_obligations.py) | Test degli obblighi: database di pacman finto, nascita, chiusura da sé, done e dismiss, campo in ogni schermata, archivio manomesso |
| [../deck/tests/test_claude_hooks.py](../deck/tests/test_claude_hooks.py) | Test degli hook di autoprompting: politica, novità del turno, verifiche dopo le azioni, registro delle sessioni |
| [../deck/tests/live_term_check.py](../deck/tests/live_term_check.py) | Controllo dal vivo di `deck term` con programmi veri sulla Deck |
| [../deck/agentdeck/components/](../deck/agentdeck/components/__init__.py) | Un modulo per componente; l'elenco dei componenti attivi è in `__init__.py` |
| [../deck/agentdeck/system.py](../deck/agentdeck/system.py) | Letture dello stato della Deck da `/proc`, `/sys` e comandi; parser puri |
| [../deck/agentdeck/wifi_switch.py](../deck/agentdeck/wifi_switch.py) | Cambio Wi-Fi con ritorno automatico, eseguito come root in un'unità transitoria |
| [../deck/tests/test_deck.py](../deck/tests/test_deck.py) | Test di conformità, iniezione, parametri, conferme, guasti |
| [../deck/tests/test_status.py](../deck/tests/test_status.py) | Test di `/status`: parser su output reali, avvisi, nomi esterni nei soli dati |
| [../deck/tests/test_snapshot.py](../deck/tests/test_snapshot.py) | Test di `/snapshot`: elenco, creazione, rollback, rifiuti di sicurezza, guasti |
| [../deck/tests/test_network.py](../deck/tests/test_network.py) | Test di `/network`: scansione, reti sorelle, avvisi, SSID malevoli, LLMNR, cambio Wi-Fi, profili iwd |
| [../deck/tests/live_network_check.py](../deck/tests/live_network_check.py) | Controllo dal vivo di `deck network` contro `ip`, `iw`, `resolvectl`, `ss` |
| [../deck/tests/test_service.py](../deck/tests/test_service.py) | Test di `/service`: parser di `systemctl`, protezione dell'accesso, anteprime, azioni, snapshot, testo esterno |
| [../deck/tests/live_service_check.py](../deck/tests/live_service_check.py) | Controllo dal vivo di `deck service` contro `systemctl`, con un servizio di prova |
| [../deck/tests/test_logs.py](../deck/tests/test_logs.py) | Test di `/logs`: righe reali del journal, traccia dell'agente esclusa, filtri, righe malevole, collegamento da `/service` |
| [../deck/tests/live_logs_check.py](../deck/tests/live_logs_check.py) | Controllo dal vivo di `deck logs` contro `journalctl -o json`, con una riga malevola |
| [../deck/tests/test_update.py](../deck/tests/test_update.py) | Test di `/update`: `pacman -Qu`, riavvio e GRUB, anteprima, snapshot, verifica, rollback indicato, testo esterno |
| [../deck/claude/](../deck/claude/install.sh) | Configurazione di Claude Code per AgentDeck: stile, CLAUDE.md, impostazioni gestite, guardia, inizio sessione ([claude-code.md](claude-code.md)) |
| [../deck/tests/test_claude_config.py](../deck/tests/test_claude_config.py) | Test della guardia, dell'hook di inizio sessione e del CLAUDE.md generato |
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
4. collega `/usr/local/bin/deck` a `/opt/agentdeck/deck`, e installa l'hook di pacman degli obblighi in
   `/etc/pacman.d/hooks/`, con il suo script in `/usr/local/lib/agentdeck/` ([obblighi.md](obblighi.md));
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

Le sue azioni diventano da sole strumenti del server MCP (`<componente>_<azione>`): non serve altro codice.
