# Architettura agent-first di AgentDeck

Studio del ciclo 03: com'è fatto il sistema e in che punti la sua architettura si può intercettare e cambiare,
perché AgentDeck diventi un sistema operativo pensato **solo per agenti**. L'umano arriverà più avanti, con
interfacce effimere.

> **Stato:** studio in corso, nessuna modifica alla Deck. Le proposte (identificativi `A<sezione>.<numero>`)
> sono da rivedere con l'utente a studio finito: ognuna avrà una decisione esplicita prima di diventare
> sviluppo.

## Metodo

Ogni strato del sistema risponde a quattro domande, con dati misurati sulla Deck e non presi a memoria:

1. **Come funziona**: componenti, configurazione, tempi, interfacce che espone.
2. **Presupposti umani**: dove il sistema dà per scontato che qualcuno guardi uno schermo, prema un tasto, scriva
   una password o legga un testo.
3. **Punti di intercettazione**: dove il comportamento si può cambiare (configurazioni, unità, hook, API,
   componenti sostituibili).
4. **Proposte**, ordinate per livello di intervento ([../PRINCIPI.md](../PRINCIPI.md), INV-10):

| Livello | Cosa significa |
|---|---|
| L1 configurazione | Si cambia un'impostazione del sistema esistente |
| L2 strato nostro | Un componente nostro (`deck` o un'unità di AgentDeck) usa ciò che c'è |
| L3 sostituzione | Un componente del sistema lascia il posto a un altro esistente |
| L4 codice di base | Si modifica il codice di kernel o programmi di sistema: solo con un bisogno reale e una decisione esplicita |

Ogni proposta si misura con i due principi del progetto:
- **interattività**: ogni azione è una schermata con dati, azioni, anteprime e conferme;
- **autoprompting**: il sistema dà all'agente le istruzioni giuste nel momento in cui servono.

## Indice

1. [Avvio, kernel e ripristino](#1-avvio-kernel-e-ripristino) (O8.T1)
2. [Init, servizi e interfacce del sistema](#2-init-servizi-e-interfacce-del-sistema) (O8.T2)
3. Identità, permessi, isolamento e segreti (O8.T3)
4. Stato del sistema, software e snapshot (O8.T4)
5. Eventi, log e osservabilità (O8.T5)
6. L'harness dell'agente (O8.T6)
7. Sintesi: architettura proposta e decisioni (O8.T7)

---

## 1. Avvio, kernel e ripristino

### 1.1 Come funziona oggi

Misure del 25/10/2026 sulla Deck (`systemd-analyze`, `bootctl status`, `efibootmgr -v`, configurazioni):

| Fase | Componente | Tempo | Dettagli |
|---|---|---|---|
| Firmware | UEFI di Valve, BIOS F7A0120 (12/2023) | 7,0 s | Secure Boot **disabilitato, in setup mode** (nessuna chiave registrata); **TPM 2.0** presente (`/dev/tpm0`); "Boot into firmware" supportato |
| Bootloader | GRUB 2.16 da `/efi/EFI/GRUB/grubx64.efi` (copia di riserva in `EFI/BOOT/BOOTX64.EFI`) | 4,2 s | Menu con `GRUB_TIMEOUT=2`; 16 voci più il sottomenu degli snapshot di grub-btrfs (65 voci); `GRUB_DEFAULT=0`; `grubenv` vuoto |
| Kernel e initramfs | `linux` 7.2.11 (predefinito con `GRUB_TOP_LEVEL`), `linux-lts` 6.18 di riserva | 6,2 s | Kernel e initramfs (circa 50 MB) stanno in `/boot`, dentro il subvolume `@`; initramfs classico con udev e hook `grub-btrfs-overlayfs` |
| Spazio utente | systemd 262 fino a `graphical.target` | 2,8 s | Catena critica: dbus, iwd, rete, `sshd` a 2,06 s; Wi-Fi e DHCP portano SSH raggiungibile a circa 30 s dall'accensione |

- **Riga di comando del kernel:** `root=UUID=… rw rootflags=subvol=@ loglevel=3`.
- **Ordine di avvio UEFI:** `GRUB` per primo; la chiavetta live (`Boot0000`) resta registrata e si può
  scegliere per un solo avvio con `BootNext`, come abbiamo fatto in installazione.
- **EFI:** partizione da 2 GB di cui 720 KB usati; contiene solo i due binari di GRUB.
- **Journal:** persistente. Oggi registra 7 avvii, 32 MB in tutto, ed è leggibile dopo un avvio fallito.
- **Microcodice:** `amd-ucode` è installato, ma il kernel avvisa che il microcodice della APU (revisione
  `0x08900201`) non contiene la correzione per Zenbleed. L'avviso esiste solo nei messaggi del kernel.

### 1.2 Presupposti umani

| # | Dove | Cosa succede oggi | Effetto per un agente |
|---|---|---|---|
| H1 | **Shell d'emergenza** (`emergency.service`, `rescue.service`) | Se l'avvio fallisce, ad esempio per un disco o un `fstab` sbagliato, systemd lancia `systemd-sulogin-shell`, che chiede la password di root alla console. **L'account root è bloccato** (`passwd -S root` dà `L`), quindi sulogin non può entrare e aspetta che qualcuno prema Invio. La rete non è attiva | La Deck resta ferma e irraggiungibile finché un umano non interviene. È il rischio più grave per INV-1 |
| H2 | **Kernel panic** | `kernel.panic=0`: dopo un panic la macchina resta ferma con il messaggio sullo schermo | Ferma per sempre, finché qualcuno non tiene premuto il tasto di accensione |
| H3 | **Blocco totale** | Due watchdog hardware esistono (`sp5100_tco` del chipset AMD, `wdat_wdt` di ACPI), ma systemd non li usa (`RuntimeWatchdogSec` spento) | Un blocco del kernel o di PID 1 non si recupera da solo |
| H4 | **Menu di GRUB** | La scelta di un altro kernel o di uno snapshot si fa con la tastiera, entro 2 secondi; `GRUB_DEFAULT=0` rende inefficace `grub-reboot` | Un agente non può provare un kernel o uno snapshot per un solo avvio, con ritorno automatico |
| H5 | **Firmware** | Impostazioni del BIOS e menu di avvio solo con i tasti fisici (Volume + o − con Accensione); aggiornamenti del BIOS pensati per arrivare con SteamOS | Fuori dalla portata dell'agente, salvo `systemctl reboot --firmware-setup`, che serve comunque a un umano |
| H6 | **Controllo della partizione EFI** | `/efi` ha il controllo del filesystem all'avvio (campo 2 di `fstab`) e non è `nofail` | Un problema della partizione EFI porta alla shell d'emergenza (H1), anche se l'EFI non serve per arrivare a SSH |
| H7 | **Messaggi a schermo** | Esito dell'avvio, avvisi del kernel, microcodice: tutto scritto per chi guarda la console | Nessun esito strutturato dell'avvio: l'agente deve cercarlo nel journal |
| H8 | **Chiavetta di ripristino** | Va inserita a mano | Una volta inserita, l'agente può sceglierla con `BootNext`, ma solo se la Deck è ancora raggiungibile |

### 1.3 Punti di intercettazione

- **sysctl** (`/etc/sysctl.d/`): `kernel.panic`, `kernel.panic_on_oops`, `kernel.hung_task_panic`.
- **systemd, `system.conf`**: `RuntimeWatchdogSec`, `RebootWatchdogSec` e `WatchdogDevice` attivano il
  watchdog hardware.
- **Unità di emergenza**: `emergency.service`, `rescue.service`, `emergency.target` si possono sovrascrivere con
  drop-in. Al posto della shell che aspetta un umano si può portare la Deck in uno stato che l'agente raggiunge
  (rete e sshd) oppure farla ripartire da uno stato buono.
- **`boot-complete.target`** e **`systemd-bless-boot`** (presenti in systemd 262): il punto in cui si dichiara
  riuscito un avvio. `systemd-bless-boot` funziona solo con systemd-boot.
- **GRUB**: `GRUB_DEFAULT=saved` con `grub-reboot` per scegliere la voce di un solo avvio; `grubenv` come
  memoria fra un avvio e l'altro; gli script in `/etc/grub.d/`.
- **EFI**: `BootNext` e `BootOrder` dalle variabili EFI, scrivibili da Linux; `bootctl` per leggerle.
- **Soft-reboot** (`systemctl soft-reboot`, systemd 254 e successivi): riavvia tutto lo spazio utente senza
  riavviare il kernel, in pochi secondi.
- **Secure Boot in setup mode e TPM 2.0**: si possono registrare chiavi nostre e misurare l'avvio, ad esempio
  per sigillare i segreti allo stato del sistema (sezione 3).

### 1.4 Proposte

| Id | Livello | Proposta | Perché, per l'agente |
|---|---|---|---|
| A1.1 | L1 | `kernel.panic=10` e `kernel.panic_on_oops=1`: dopo un panic la Deck riparte da sola | Elimina H2 |
| A1.2 | L1 | Watchdog hardware con `RuntimeWatchdogSec=30s` e `RebootWatchdogSec=10min` su `sp5100_tco` | Elimina H3: un blocco diventa un riavvio |
| A1.3 | L1 | `/efi` con `nofail` e `x-systemd.device-timeout`, senza controllo all'avvio | Elimina H6: l'EFI non blocca più l'avvio |
| A1.4 | L1/L2 | **Emergenza raggiungibile**: un drop-in fa entrare `emergency.target` in uno stato minimo di AgentDeck con rete, sshd e journal, invece della shell che aspetta un umano. Se l'agente non conferma entro N minuti, la Deck riparte dall'ultimo avvio buono (A1.6) | Elimina H1, il rischio più grave. L'agente entra con la sua chiave e trova le istruzioni (autoprompting): perché si è fermata, quale snapshot è l'ultimo buono, come tornarci |
| A1.5 | L1 | `GRUB_DEFAULT=saved`, `grub-reboot` per gli avvii di prova, menu nascosto con `GRUB_TIMEOUT=0` (2 s in meno) | Rende possibile scegliere a distanza la voce di un solo avvio (H4) |
| A1.6 | L2 | **Avvio di prova con conferma**, il boot counting fatto da noi: un avvio nuovo (kernel, snapshot, configurazione) parte come prova. Un'unità di AgentDeck verifica rete, sshd e `deck`; se tutto è a posto entro N minuti registra l'avvio come buono (`boot-complete.target`). Altrimenti, o se il watchdog interviene, il riavvio successivo torna all'ultima voce buona | È lo stesso schema del cambio Wi-Fi e della rete di sicurezza SSH: **cambio, prova, conferma oppure ritorno automatico**. Funziona con GRUB e mette al sicuro kernel e snapshot |
| A1.7 | L2 | **`deck boot`**: storia degli avvii con esito strutturato (riuscito, ritornato indietro, emergenza, watchdog), tempi per fase, prossimo avvio con anteprima e ritorno automatico (kernel di riserva, snapshot), riavvio, soft-reboot, stato di watchdog, Secure Boot e TPM. Avviso di autoprompting al primo accesso dopo un avvio anomalo | Toglie H7: niente più esiti da cercare a mano nel journal |
| A1.8 | L2 | `systemctl soft-reboot` per i cambi che toccano solo lo spazio utente | Riparte in pochi secondi senza passare dal firmware (7 s) e da GRUB (4 s) |
| A1.9 | L2 | Avviso strutturato per il microcodice non aggiornato (Zenbleed) e per il BIOS, con verifica dell'aggiornamento del BIOS della Deck fuori da SteamOS | Toglie la dipendenza da messaggi che solo un umano legge (H5, H7) |
| A1.10 | L3 | **systemd-boot con kernel unificati (UKI)** al posto di GRUB, sulla partizione EFI da 2 GB. Porta il boot counting nativo (`+tries`, `systemd-bless-boot`), la scelta del prossimo avvio con `systemctl reboot --boot-loader-entry=`, lo stato in JSON con `bootctl --json`, e Secure Boot con chiavi nostre e avvio misurato con il TPM | API strutturate al posto di script e menu. Il costo: il kernel esce dagli snapshot di Btrfs e va tenuto in copia per ogni stato a cui si può tornare (lo spazio c'è); si perde il menu degli snapshot di grub-btrfs, che serve a un umano. Inverte il limite N17: il bootloader non è più legato agli snapshot |
| A1.11 | L3 | initramfs basato su systemd (`sd-initrd`) al posto di quello con udev, se si sceglie A1.10 | Serve per UKI, TPM e avvio misurato; oggi è bloccato da `grub-btrfs-overlayfs` |

**Il limite N17**, cioè GRUB nell'EFI e i moduli negli snapshot:
- con GRUB (A1.5-A1.6) si risolve reinstallando, dopo un rollback, il GRUB dello snapshot di destinazione;
- con systemd-boot (A1.10) il problema cambia forma: sono il kernel e l'initramfs a stare fuori dagli snapshot.

**Da decidere nella sintesi:**
- **A1.10 o A1.5-A1.6.** Resto su GRUB con il boot counting fatto da noi, oppure passo a systemd-boot con le API
  native. A1.1-A1.4 valgono in tutti e due i casi.
- **Soglie:** i minuti di conferma degli avvii di prova e il comportamento dopo più ritorni consecutivi.

**Verifiche aperte** per lo sviluppo:
- che `sp5100_tco` regga davvero un riavvio forzato;
- che la Deck si riaccenda da sola al ritorno della corrente. Su questo hardware non è ancora misurato.

---

## 2. Init, servizi e interfacce del sistema

### 2.1 Come funziona oggi

L'agente parla con la Deck in un solo modo: **SSH, poi bash, poi un comando**. `deck` aggiunge un livello
strutturato, ma dietro lancia 35 comandi e legge il loro output con 12 parser di testo
([../deck/agentdeck/system.py](../deck/agentdeck/system.py)). Il sistema però offre molto di più, misurato il
25/10/2026:

| Interfaccia | Cosa c'è sulla Deck | Forma |
|---|---|---|
| **varlink** di systemd 262 | 18 socket in `/run/systemd/io.systemd.*`, con 27 interfacce nel registro `/run/varlink/registry`: `Manager` (riavvio, soft-reboot, kexec), `Unit` (`List`, `SetProperties`, `StartTransient`), `Network`, `Resolve` e `Resolve.Monitor`, `Journal`/`JournalAccess`, `Login`, `Hostname`, `BootControl`, `Credentials`, `SysUpdate`, `sysext`, `Repart`, `UserDatabase` | JSON tipizzato, con l'interfaccia descritta in un IDL leggibile da macchina (`varlinkctl introspect`). `io.systemd.Unit.List` su `sshd.service` risponde con configurazione e stato completi in **8 ms** |
| **D-Bus** di sistema | `org.freedesktop.systemd1`, `network1`, `resolve1`, `login1`, `timesync1`, `net.connman.iwd` | Tipizzato; `busctl --json=short`. iwd dà lo stato della stazione e le reti note con il **nome esatto**, senza testo da interpretare |
| **Comandi con JSON** | `systemctl --output=json`, `networkctl`, `resolvectl`, `loginctl`, `hostnamectl`, `userdbctl`, `bootctl` (`--json`), `ip -j`, `lsblk -J`, `findmnt -J`, `snapper --jsonout`, `btrfs --format json`, `smartctl -j`, `journalctl -o json` | JSON |
| **Comandi solo testo** | `ss`, `iw`, `pacman`, `free`, `df`, `iwctl` (anche con codici colore), `timedatectl` (coppie chiave=valore) | Testo per terminale |
| **File del kernel** | `/proc` (memoria, processi, rete), `/sys` (batteria, sensori, rete, schermo, watchdog) | Un valore per file, o righe semi-strutturate |
| **Unità e drop-in** | Configurazione dichiarativa di servizi, timer, socket, mount | File INI; li legge e li scrive anche un agente |

`deck` usa testo anche dove esiste di meglio:
- gli **snapshot** sono letti dalla tabella di `snapper list`, mentre `snapper --jsonout` c'è;
- lo **stato dei servizi** passa da `systemctl show`, circa 220 ms per 111 unità, mentre varlink risponde in
  millisecondi;
- il **Wi-Fi** passa da `iw` e `iwctl`, mentre iwd ha un'API D-Bus completa.

Le trappole P11 (nome di rete trovato per prefisso) e P12 (`iwctl` che non vede la rete) sono nate proprio dal
testo.

### 2.2 Presupposti umani

| # | Dove | Cosa succede | Effetto per un agente |
|---|---|---|---|
| H9 | Output dei comandi | Tabelle allineate alla larghezza del terminale, colori, intestazioni, unità di misura arrotondate (`df -h`), messaggi tradotti secondo `LANG` | Parser fragili che si rompono a ogni cambio di versione o di lingua |
| H10 | Pager | `systemctl`, `journalctl` e simili aprono `less` quando c'è un terminale | Con un terminale l'agente resta bloccato; senza, oggi va bene per caso: nessuna variabile `PAGER` o `SYSTEMD_PAGER` è impostata |
| H11 | Domande interattive | `pacman` senza `--noconfirm`, `iwctl` che chiede la passphrase, `systemctl edit` che apre un editor, `ssh` con una chiave host nuova, gli agenti di autenticazione di polkit | Comandi che aspettano una risposta: violano INV-2 |
| H12 | Errori | Messaggi in testo libero su stderr; i codici di uscita cambiano significato da un programma all'altro (`systemctl is-system-running` esce con 1 quando lo stato è "degraded") | L'agente deve interpretare frasi |
| H13 | Scoperta | Le capacità si imparano da `--help` e dalle pagine `man`, scritte per persone | L'agente scopre leggendo prosa, invece di un elenco di azioni con i loro parametri |
| H14 | Nessuna traccia d'intenzione | Il sistema registra cosa è successo (journal), non chi l'ha chiesto e perché | Nessun legame fra la richiesta dell'agente e i suoi effetti |

### 2.3 Punti di intercettazione

- **Dal lato dell'output:**
  - le API native, cioè varlink, D-Bus e i flag JSON, al posto del testo;
  - `/proc` e `/sys` letti direttamente;
  - le variabili d'ambiente delle sessioni dell'agente (`SYSTEMD_PAGER`, `SYSTEMD_COLORS`, `NO_COLOR`, `LANG`),
    impostabili per l'utente `agent` con `SetEnv` di sshd o con `environment.d`.
- **Dal lato dei comandi:**
  - la sessione SSH: `ForceCommand` e la riga `BASH_ENV` che usiamo già per lo schermo;
  - il comando `deck`;
  - un servizio varlink o D-Bus nostro, che il sistema pubblica e rende scopribile;
  - un server MCP, per gli harness degli agenti (sezione 6).
- **Lavoro dell'agente come unità transitorie:** `StartTransient` di varlink o `systemd-run`, che già usiamo per
  il cambio Wi-Fi e per gli aggiornamenti. Ogni lavoro lungo diventa un'unità con un nome, i suoi log, limiti di
  risorse, uno stato interrogabile e la possibilità di fermarlo.
- **Autorizzazione:** polkit per le chiamate D-Bus e i permessi dei socket varlink. Ne parla la sezione 3.

### 2.4 Proposte

| Id | Livello | Proposta | Perché, per l'agente |
|---|---|---|---|
| A2.1 | L1 | Ambiente delle sessioni dell'agente pensato per macchine: `SYSTEMD_PAGER=cat`, `PAGER=cat`, `SYSTEMD_COLORS=0`, `NO_COLOR=1`, lingua fissa `C.UTF-8` | Toglie H9 (in parte) e H10 senza toccare i programmi |
| A2.2 | L2 | **`deck` passa alle API native:** varlink per servizi, rete, nomi e journal; D-Bus di iwd per il Wi-Fi; JSON per snapshot (`snapper --jsonout`), Btrfs, dischi e mount; `/proc` e `/sys` letti direttamente. Il testo resta solo dove non esiste altro (`ss`, `iw scan`, `pacman`), ognuno con un piano per toglierlo | Più veloce (ms invece di centinaia di ms), indipendente da versione e lingua, senza le trappole del testo (P11, P12) |
| A2.3 | L2 | **AgentDeck come servizio di sistema**: le schermate di `deck` esposte anche come interfaccia varlink `io.agentdeck.*`, su un socket in `/run/agentdeck/`. L'IDL descrive azioni e parametri tipizzati; `deck` diventa uno dei client, e lo stesso protocollo si serve a MCP (sezione 6) | Interattività nativa: le azioni si scoprono e si chiamano come API del sistema, non come comandi da leggere |
| A2.4 | L2 | **Sessione dell'agente con una regia:** la riga che oggi registra i comandi per lo schermo diventa il punto in cui ogni comando grezzo viene registrato in modo strutturato (comando, intenzione dichiarata, durata, codice di uscita, effetti), con l'ambiente di A2.1. Se il comando ha un equivalente in `deck`, compare un suggerimento (autoprompting); i programmi interattivi che bloccherebbero vanno avvolti | Toglie H11, H12 e H14 anche per i comandi che non passano da `deck`. Va fatto con la rete di sicurezza SSH, come la registrazione dello schermo |
| A2.5 | L2 | **Lavori dell'agente come unità transitorie**, con un componente `deck jobs`: elenco, stato, log, annullamento | Il lavoro dell'agente diventa osservabile e gestibile come quello di un servizio, e sopravvive alla caduta di SSH |
| A2.6 | L2 | Errori strutturati per tutte le azioni: codice stabile, campo, causa e uscita suggerita, come già fa il protocollo di `deck`, estesi ai comandi della regia (A2.4) | Toglie H12 |
| A2.7 | L3 | Sostituire gli strumenti solo testo dove l'API esiste: `iwctl` e `iw link` con il D-Bus di iwd; `pacman -Q` con la lettura diretta del database locale (`/var/lib/pacman/local/*/desc`, formato stabile) o con `pyalpm` dei repository ufficiali; `ss` con `/proc/net/*` | Toglie il testo da tutto lo strato di `deck` |

**Da decidere nella sintesi:**
- quanto del vecchio "comando via SSH" resta come interfaccia primaria, rispetto al servizio varlink e MCP
  (A2.3);
- se la regia dei comandi grezzi (A2.4) va fatta, perché tocca la sessione SSH (INV-1).
