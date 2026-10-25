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
3. [Identità, permessi, isolamento e segreti](#3-identità-permessi-isolamento-e-segreti) (O8.T3)
4. [Stato del sistema, software e snapshot](#4-stato-del-sistema-software-e-snapshot) (O8.T4)
5. [Eventi, log e osservabilità](#5-eventi-log-e-osservabilità) (O8.T5)
6. [L'harness dell'agente](#6-lharness-dellagente) (O8.T6)
7. [Sintesi: architettura proposta e decisioni](#7-sintesi-architettura-proposta-e-decisioni) (O8.T7)

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

---

## 3. Identità, permessi, isolamento e segreti

### 3.1 Come funziona oggi

Misure del 25/10/2026:

| Aspetto | Stato sulla Deck |
|---|---|
| **Identità** | Un solo utente con shell di login: `agent` (uid 1000, gruppo `wheel`, password bloccata). `root` ha la password bloccata. Il sistema non distingue l'agente da un umano, né un agente da un altro o una sessione dall'altra |
| **Accesso** | SSH con una sola chiave ed25519 in `authorized_keys`, senza restrizioni (nessun `from=`, nessuna scadenza). PAM: `system-remote-login`, `system-login`. Ogni sessione è un `session-N.scope` di logind (`Remote=yes`) |
| **Privilegi** | `/etc/sudoers.d/10-agent`: `agent ALL=(ALL:ALL) NOPASSWD: ALL`. Ogni azione privilegiata avviene come root, tutta uguale. sudo (1.9.17) registra nel journal solo testo libero |
| **Autorizzazione fine** | **polkit non è installato.** Le chiamate privilegiate a D-Bus e varlink sono permesse solo a root: una richiesta dell'agente a systemd di riavviare un servizio risponde "Access denied". Oggi l'unica strada è `sudo` |
| **Isolamento** | Il kernel ha i moduli di sicurezza `capability, landlock, lockdown, yama, bpf`: Landlock e BPF LSM ci sono, SELinux e AppArmor no. Namespace utente attivi (59.054), seccomp disponibile, `systemd-nspawn` e `machinectl` inclusi in systemd. Quasi tutti i servizi girano senza sandbox: `systemd-analyze security` dà esposizione 9,4-9,6 ("UNSAFE"), iwd 6,0 |
| **Traccia** | `audit` 4.2.1 installato ma `auditd` spento. Nessuna registrazione strutturata di chi ha fatto cosa |
| **Difese di rete** | nftables e iptables installati, **nessuna regola**. In ascolto solo SSH (22) e il resolver locale (53 su loopback) |
| **Segreti** | Passphrase Wi-Fi in `/var/lib/iwd/*.psk` (root, 600); chiavi host di SSH, compresa la nuova ibrida ML-DSA di OpenSSH 10; la chiave dell'agente sta sul Mac; `secrets/wifi.env` sul Mac, fuori da git. La chiavetta live contiene la password del Wi-Fi in chiaro. Nessun archivio di segreti |
| **TPM e credenziali** | TPM 2.0 attivo (`systemd-analyze has-tpm2`: sì). I PCR da 0 a 9 sono misurati anche con GRUB. `systemd-creds` è disponibile, ma non è mai stato usato (nessun `credential.secret`). Secure Boot in setup mode (sezione 1) |

### 3.2 Presupposti umani

| # | Dove | Cosa presuppone | Effetto per un agente |
|---|---|---|---|
| H15 | sudo | Una persona fidata che ogni tanto alza i privilegi, digitando la password; un registro da leggere a occhio | Tolta la password, resta il tutto o niente: ogni errore dell'agente, o di chi ne prende la chiave, è un errore di root |
| H16 | polkit (assente) | Il modello è un dialogo che chiede la password per ogni azione amministrativa | Senza polkit non esiste una delega per azione: le API del sistema sono solo per root |
| H17 | Modello di utenti | Un utente è una persona con una shell. Nessuna nozione di più agenti, di ruoli, di sessioni dell'agente, del proprietario umano diverso dall'operatore | Impossibile dare permessi diversi a un agente di sviluppo e a un agente di casa, o revocare una sola sessione |
| H18 | Segreti | Password digitate nei prompt (`iwctl`, `sudo`, `passwd`) e file leggibili da root | Niente consegna sicura senza chat (N14); i segreti non sono legati allo stato del sistema |
| H19 | Audit | Strumento forense, acceso e letto da un amministratore | Nessuna traccia continua e strutturata delle azioni dell'agente |
| H20 | Chiave SSH | Una chiave per una persona, per sempre | Una chiave rubata vale root a vita, da qualsiasi rete |

### 3.3 Punti di intercettazione

- **SSH**:
  - opzioni in `authorized_keys` (`from=`, `restrict`, comandi forzati);
  - certificati SSH con scadenza, firmati da una nostra autorità;
  - una chiave per ogni agente o sessione.
- **sudo**:
  - regole per comando invece di `ALL`;
  - registrazione strutturata degli eventi e dell'input e output (sudo 1.9);
  - un uso di sudo come accesso di emergenza, non come strada normale.
- **polkit**: regole in JavaScript per azione D-Bus. Ad esempio: "il gruppo degli agenti può riavviare questi
  servizi senza password". Si abbina alle API native della sezione 2.
- **Sandbox di systemd** per i servizi e per i lavori transitori: `ProtectSystem`, `PrivateTmp`,
  `NoNewPrivileges`, `CapabilityBoundingSet`, `RestrictAddressFamilies`, `SystemCallFilter`, `IPAddressDeny`.
- **Landlock e BPF LSM**:
  - con Landlock un processo limita da sé file e rete, senza permessi di root; è adatto ai programmi che
    l'agente lancia su dati non fidati;
  - con BPF LSM si possono scrivere politiche di sistema.
- **Container**: `systemd-nspawn`, già presente, per isolare carichi di lavoro e ambienti degli agenti.
- **Segreti**:
  - `systemd-creds` cifra con il TPM e con una chiave della macchina;
  - le unità li ricevono con `LoadCredentialEncrypted`, senza che passino da file in chiaro;
  - il TPM sigilla i segreti ai PCR: diventano inutilizzabili se la catena di avvio cambia.
- **Audit**: regole su `execve` con `auid=1000`, cioè l'utente con cui si è entrati, e sulle scritture in
  `/etc`. Ne viene una traccia completa anche per i comandi che non passano da `deck`.
- **Firewall**: nftables con ingresso chiuso salvo SSH dalla rete di casa e mDNS.

### 3.4 Proposte

| Id | Livello | Proposta | Perché, per l'agente |
|---|---|---|---|
| A3.1 | L1 | Chiave dell'agente limitata alla rete di casa (`from="192.168.1.0/24"`) e firewall nftables con ingresso chiuso salvo SSH dalla LAN e mDNS | Rafforza INV-5 e riduce H20 senza cambiare nulla per l'agente. Da fare con la rete di sicurezza SSH |
| A3.2 | L2 | **Identità degli agenti**: proprietario umano, agenti con nome (ad esempio sviluppo, casa, interno) e sessioni. Ogni agente ha la sua chiave o un certificato SSH a scadenza; ogni sessione ha un identificativo che segue le sue azioni | Toglie H17 e H20: permessi e revoca per agente, e traccia per sessione |
| A3.3 | L2 | **Broker dei privilegi** al posto di `sudo ALL`. L'agente lavora senza privilegi; le operazioni privilegiate passano dal servizio di AgentDeck (A2.3), che gira come root e per ogni azione applica la politica: permessa, da confermare con anteprima, rifiutata (le protezioni di INV-1 che `deck` ha già). Registra intenzione ed esito. `sudo` resta come accesso di emergenza, registrato per intero | È l'equivalente agentico di polkit e dei servizi di autorizzazione di macOS: i permessi si danno per azione e non per programma. Toglie H15 |
| A3.4 | L1/L3 | polkit con regole per il gruppo degli agenti, così le API D-Bus e varlink del sistema si usano senza sudo, azione per azione | È lo strato di sistema su cui poggia A3.3, e rende possibile A2.2 senza root |
| A3.5 | L2 | **Isolamento per default**: i lavori dell'agente (A2.5) girano in unità transitorie con sandbox; i programmi lanciati su dati non fidati, come contenuti scaricati o repository di terzi, con Landlock; i carichi di lavoro e gli ambienti degli agenti in container `systemd-nspawn` (sezione 4) | Un errore o un'iniezione resta confinato. Abbassa l'esposizione oggi a 9,6 |
| A3.6 | L2 | **`deck secrets`** (N14) su `systemd-creds`: cifratura con TPM e chiave della macchina, consegna alle unità con `LoadCredentialEncrypted`. L'agente vede solo nomi e metadati; i canali di consegna da parte dell'umano sono quelli di N14 | Toglie H18: segreti mai in chat e mai in chiaro su disco |
| A3.7 | L3 | Secure Boot con chiavi nostre (`sbctl`, dai repository ufficiali) e segreti sigillati al PCR 7. Va insieme ad A1.10 | Un segreto si apre solo se la Deck parte dal sistema che conosciamo |
| A3.8 | L1 | `auditd` attivo, con regole su `execve` dell'agente e sulle scritture in `/etc` e in `/var/lib/iwd`; sudo con registrazione strutturata | Toglie H19: la traccia completa è un dato, che `deck` legge (sezione 5) |

**Da decidere nella sintesi:**
- **A3.3**, la decisione più grossa di questa sezione: l'agente è root con protezioni, come oggi, oppure lavora
  senza privilegi e passa da un broker. La seconda strada è più sicura e più agentica, ma richiede prima il
  servizio di A2.3.
- **A3.2:** quanti agenti diversi prevediamo all'inizio.

---

## 4. Stato del sistema, software e snapshot

### 4.1 Come funziona oggi

Misure del 25/10/2026:

| Aspetto | Stato sulla Deck |
|---|---|
| **Disco** | Btrfs su 2 TB, **2,8 GB usati**. Subvolumi: `@` (sistema, compresi `/boot`, `/etc`, `/opt` e `/var`), `@home`, `@log` (`/var/log`), `@pkg` (cache di pacman, 1 GB), `@snapshots`, più `@old-20261025-180914`, lasciato dal rollback di prova con due subvolumi annidati creati da systemd (`var/lib/machines`, `var/lib/portables`) |
| **Snapshot** | 32 snapshot con snapper: 3 coppie pre e post di snap-pac (pulizia `number`, limite 20), 7 a orario (`timeline`, 5 orari e 7 giornalieri), **19 "single" senza pulizia**: installazione, prove e tutti quelli creati da `deck` prima di ogni modifica. Snapper non toglierà mai questi ultimi (N15). Le quote di Btrfs sono spente, quindi lo spazio di ogni snapshot non si conosce e `SPACE_LIMIT` non ha effetto |
| **Ritorno indietro** | `deck snapshot rollback` scambia `@` con una copia dello snapshot (sezione O3 del ciclo 01); oppure si avvia uno snapshot in sola lettura dal menu di grub-btrfs, che però serve a un umano (sezione 1) |
| **Software** | pacman: 224 pacchetti, 31 installati esplicitamente, nessuno esterno ai repository, nessun orfano. 37 hook di pacman, fra cui snap-pac (snapshot prima e dopo), mkinitcpio, il riavvio di sshd e gli hook di systemd. `pacman.conf` con le impostazioni predefinite (`ParallelDownloads = 5`, firme obbligatorie) |
| **Configurazione** | **Imperativa**: `install/install.sh` scrive i file, `deck` scrive drop-in. La configurazione di AgentDeck sono **24 file in `/etc` che nessun pacchetto possiede**: rete, sshd, sudo, iwd, resolved, snapper, mkinitcpio, zram, l'unità dello schermo. Per i file dei pacchetti, `pacman -Qkk` segnala come cambiato solo `/etc/resolv.conf`, ma l'installatore ha modificato anche `/etc/default/grub` |
| **Registro del software** | `/var/log/pacman.log` (225 operazioni) sta in `@log` e non torna indietro con un rollback. Dopo il rollback di prova dice ancora che `tree` è installato, mentre il sistema non lo ha più |
| **Nostro strato** | `/opt/agentdeck` (812 KB), copiato con rsync da `deck/install.sh` dentro `@`: un rollback lo porta indietro insieme al sistema (P9) |
| **Strumenti a immagini già presenti** | `systemd-sysext` e `systemd-confext`, cioè estensioni in sola lettura che si attivano e disattivano in un colpo su `/usr`, `/opt` e `/etc`. Poi `portablectl` per i servizi portabili, `systemd-nspawn`, `machinectl`, `importctl`, e l'interfaccia varlink `io.systemd.SysUpdate`. Nessuna estensione attiva; `mkosi` non è installato |

### 4.2 Presupposti umani

| # | Dove | Cosa presuppone | Effetto per un agente |
|---|---|---|---|
| H21 | Aggiornamenti di Arch | Che qualcuno legga le notizie di archlinux.org prima di aggiornare (gli "interventi manuali richiesti") e unisca a mano i file `.pacnew` con `pacdiff` | Informazioni critiche in prosa su un sito, e unioni fatte a occhio |
| H22 | Configurazione | File modificati a mano, nessun registro dello stato voluto | Le differenze fra lo stato voluto e quello reale non si vedono: deriva invisibile |
| H23 | Snapshot | Un umano che sceglie da un elenco con date e descrizioni libere | Nessuna nozione di "ultimo stato buono"; scegliere a cosa tornare è un giudizio |
| H24 | Pulizia | Cancellazioni manuali (`@old`, snapshot singoli) | Lo spazio si consuma in silenzio; oggi non è un problema (1%), ma lo diventerà |
| H25 | Registro | Il log di pacman come racconto cronologico, senza collegamento agli snapshot | Dopo un rollback la storia e lo stato reale divergono |

### 4.3 Punti di intercettazione

- **snapper**:
  - algoritmi di pulizia per snapshot (`number`, `timeline`) e i dati utente (`important=yes`), cioè ciò che
    `deck` assegna quando crea uno snapshot;
  - i limiti nella configurazione;
  - `--jsonout` per leggere.
- **Quote di Btrfs**: le quote semplici (squota) o i qgroup danno lo spazio esclusivo di ogni snapshot, con
  costi diversi.
- **Disposizione dei subvolumi**: un subvolume a parte per lo strato di AgentDeck lo terrebbe fuori dai
  rollback del sistema (P9); così anche i carichi di lavoro, ognuno con i suoi snapshot.
- **Hook di pacman** (`/etc/pacman.d/hooks/`): prima e dopo ogni transazione si può controllare, registrare in
  forma strutturata, legare la transazione al suo snapshot e raccogliere i `.pacnew`.
- **Estensioni di systemd** (`sysext`, `confext`): software e configurazione come immagini in sola lettura,
  attivabili e disattivabili in modo atomico, con ritorno immediato.
- **Container e servizi portabili** (`systemd-nspawn`, `portablectl`): isolano i carichi senza pacchetti nuovi.
- **Notizie di Arch**: il feed di archlinux.org si legge come dato prima di ogni aggiornamento.

### 4.4 Proposte

| Id | Livello | Proposta | Perché, per l'agente |
|---|---|---|---|
| A4.1 | L1/L2 | **Politica degli snapshot**: quelli automatici di `deck` con pulizia `number` (limite configurabile), quelli che proteggono qualcosa di importante marcati `important`; quote semplici di Btrfs per conoscere lo spazio di ognuno; eliminazione con anteprima di `@old` e degli snapshot superati (O7.T2) | Chiude N15, N20 e O7.T2 con una regola invece che a mano |
| A4.2 | L2 | **Stati buoni**: uno snapshot diventa "buono" quando un avvio di prova è confermato (A1.6) o una modifica è verificata. `deck snapshot` li distingue e il rollback propone per primo l'ultimo stato buono | Toglie H23: a cosa tornare non è più un giudizio |
| A4.3 | L2 | **Stato voluto come dato**: un file dichiarativo con pacchetti espliciti, file di configurazione di AgentDeck, servizi abilitati e impostazioni di rete. `deck state` mostra le differenze con lo stato reale e le applica con anteprima e snapshot; ogni azione di `deck` lo aggiorna. `install/install.sh` diventa la prima applicazione di questo stato | Toglie H22: la deriva si vede, il sistema si riproduce, le modifiche dell'agente si possono rivedere |
| A4.4 | L2 | **Hook di pacman di AgentDeck**: ogni transazione registrata in forma strutturata (pacchetti, versioni, `.pacnew`, snapshot pre e post) e collegata allo stato voluto; i `.pacnew` diventano un avviso con le differenze nei dati | Toglie H21 (unioni) e H25 |
| A4.5 | L2 | **Notizie di Arch come dato**: `deck update` legge il feed prima di applicare e blocca l'applicazione se c'è un intervento manuale nuovo; il testo della notizia resta nei dati (INV-4) | Toglie H21 (notizie) |
| A4.6 | L3 | **Lo strato di AgentDeck fuori dal sistema**: `deck` e gli strumenti degli agenti in un'estensione `sysext` su `/opt`, oppure in un subvolume proprio. Si aggiorna e torna indietro da solo, indipendente dai rollback del sistema | Risolve P9 |
| A4.7 | L3 | **Carichi di lavoro in container**: `systemd-nspawn` o servizi portabili, ognuno con un suo subvolume e i suoi snapshot; lo stesso per gli ambienti di lavoro degli agenti (sezione 6, A3.5) | Isolamento e ritorno indietro per singolo carico, senza toccare il sistema |
| A4.8 | L3 | **Sistema a immagini**: `/usr` in sola lettura, aggiornato a immagini A/B con `systemd-sysupdate`; personalizzazioni solo con `sysext` e `confext`. È il modello dei sistemi immutabili, ad esempio quelli costruiti con mkosi, anche su base Arch | Aggiornamenti atomici e ritorno indietro banale. Il prezzo è un cambio profondo rispetto ad Arch imperativo: va valutato con INV-7 e con la sezione 1 |

**Da decidere nella sintesi:**
- **A4.3, stato voluto dichiarativo, contro A4.8, sistema a immagini.** Sono due risposte diverse allo stesso
  bisogno, sapere e ripristinare lo stato del sistema. A4.3 resta dentro Arch com'è; A4.8 cambia la forma del
  sistema.
- **A4.1** è indipendente e si può fare per primo.

---

## 5. Eventi, log e osservabilità

### 5.1 Come funziona oggi

Misure del 25/10/2026:

| Fonte | Stato sulla Deck |
|---|---|
| **Journal** | Persistente, 32 MB. Circa **1.658 righe all'ora**, di cui 462 (28%) sono la traccia dei comandi dell'agente scritta dallo schermo. Solo il **42% delle righe ha un `MESSAGE_ID`** del catalogo di systemd, cioè un evento riconoscibile da una macchina (unità avviata, fermata, fallita); il resto è prosa. `journalctl -o json` e `-f` permettono lettura e flusso; l'interfaccia varlink `io.systemd.JournalAccess` è riservata a root |
| **Segnali D-Bus** | systemd (`UnitNew`, `JobRemoved`, `PropertiesChanged`), networkd, logind, iwd. A riposo il sistema è silenzioso: **0 messaggi in 8 secondi** di osservazione |
| **udev** | Eventi del kernel per dispositivi: alimentazione (`ACAD`, `BAT1`), USB, dischi. Nessun evento in 4 secondi a riposo |
| **Timer** | Solo manutenzione: snapper (timeline, cleanup), `tmpfiles`, `man-db`, `shadow`, portachiavi di Arch. Nessuno per l'agente |
| **Unità path** | Solo `systemd-ask-password-console.path` e `-wall.path`, che portano le richieste di password alla console e ai terminali |
| **logind** | Tasto di accensione: `HandlePowerKey=poweroff`; pressione lunga e inattività: `ignore` |
| **Pressione delle risorse** | PSI attivo (`/proc/pressure/{cpu,memory,io}`); `systemd-oomd` presente ma spento; `systemd-coredump` presente, nessun crash |
| **Audit** | Spento (sezione 3) |
| **Avvisi di `deck`** | Calcolati solo quando l'agente apre una schermata. Nessuna storia, nessun "nuovo dall'ultima volta", nessuna notifica |

**Nessuno sveglia l'agente.** L'agente esiste solo mentre un umano apre una sessione dal Mac. Se di notte un
servizio fallisce, il disco si riempie o un aggiornamento di sicurezza esce, lo si scopre alla sessione dopo,
e solo se si apre la schermata giusta.

### 5.2 Presupposti umani

| # | Dove | Cosa presuppone | Effetto per un agente |
|---|---|---|---|
| H26 | Monitoraggio | Qualcuno che guarda uno stato o una dashboard quando vuole (pull) | L'agente non viene avvisato: ciò che succede fra una sessione e l'altra si perde, finché non va a cercarlo |
| H27 | Log in prosa | Messaggi da leggere: il 58% senza un identificativo di evento | Riconoscere un evento vuol dire interpretare frasi, e il testo dei log è non fidato (INV-4) |
| H28 | Tasto di accensione | Una persona che lo preme vuole spegnere | Un tocco per errore spegne il server senza che l'agente lo sappia o possa salvare lo stato |
| H29 | Richieste di password | Console e terminali come canale per le domande del sistema (`ask-password`) | Domande che nessuno vedrà e che bloccano |
| H30 | Notifiche | `wall` e messaggi alla console | Un canale che l'agente non riceve |

### 5.3 Punti di intercettazione

- **`OnFailure=` per tutte le unità**: un drop-in di primo livello (`/etc/systemd/system/service.d/`) fa partire
  una nostra unità a ogni guasto di qualsiasi servizio, con il nome del servizio come parametro.
- **Segnali D-Bus e varlink** con filtri: cambi di stato delle unità, della rete, delle sessioni, del Wi-Fi.
- **Regole udev** che avviano unità (`SYSTEMD_WANTS`) all'arrivo di un dispositivo o a un cambio di
  alimentazione.
- **Unità path**: inotify su file e cartelle, ad esempio i `.pacnew`, `/etc` o la cartella dei segreti in
  arrivo (N14).
- **Timer** con `OnCalendar` e `OnBootSec` per i controlli periodici dell'agente.
- **PSI**: soglie di pressione con notifica (poll su `/proc/pressure/*`), e `systemd-oomd` per i limiti di
  memoria per gruppo di unità.
- **journald**:
  - campi strutturati propri (`AGENTDECK_*`) per gli eventi e le azioni dell'agente;
  - namespace o file separati per tenere la traccia dell'agente fuori dal journal di sistema.
- **logind**: `HandlePowerKey=ignore`, con il tasto trattato come evento.
- **auditd** (sezione 3) con i suoi plugin per inoltrare gli eventi.

### 5.4 Proposte

| Id | Livello | Proposta | Perché, per l'agente |
|---|---|---|---|
| A5.1 | L1 | La **traccia dei comandi dell'agente fuori dal journal di sistema**, in un namespace di journald o in un registro suo | Il journal di sistema torna ai fatti del sistema (oggi il 28% è traccia); niente più filtri come quello di `deck logs` (P14) |
| A5.2 | L1/L2 | **`OnFailure=` globale**: ogni servizio che fallisce produce un evento strutturato (unità, risultato, ultime righe del journal nei dati) | Nessun guasto passa inosservato |
| A5.3 | L2 | **Raccoglitore di eventi di AgentDeck**, `agentdeck-events`. Ascolta segnali D-Bus, udev, PSI, journal (solo eventi con `MESSAGE_ID` o priorità alta), timer e le soglie degli avvisi di `deck`. Li trasforma in eventi uniformi: identificativo, ora, fonte, codice stabile, gravità, dati. Li tiene in una coda persistente con deduplica e stato (nuovo, visto, gestito) | Toglie H26 e H27: un solo flusso di eventi, già in forma di dato |
| A5.4 | L2 | **Briefing di inizio sessione**, `deck inbox`: alla prima chiamata di una sessione l'agente riceve gli eventi nuovi dall'ultima volta, ordinati per gravità, con l'azione suggerita per ciascuno. Le istruzioni sono scritte dal sistema; il contenuto degli eventi sta nei dati | È l'autoprompting nel momento giusto: l'agente sa da dove cominciare. Chiude l'attrito 2 del punto della situazione |
| A5.5 | L2 | **Risveglio dell'agente**: regole per evento decidono se basta accodarlo per la prossima sessione o se serve un agente subito. In quel caso parte una sessione senza interfaccia dell'harness (sezione 6), con l'evento come contesto iniziale. Limiti di frequenza e di costo delle API | Il passo che rende la Deck autonoma: è il trigger dell'agente interno |
| A5.6 | L2 | **Registro delle azioni dell'agente**: ogni azione di `deck` e ogni comando della regia (A2.4) con sessione, intenzione, anteprima, esito e snapshot, in campi strutturati. Da qui escono i riepiloghi delle sessioni agentiche | Memoria di cosa si è fatto e perché; è la base per annullare e per riassumere |
| A5.7 | L2 | **Avvisi con una storia**: ogni avviso di `deck` ha la prima comparsa, l'ultima, quando si è risolto, quante volte è tornato | Distingue un problema nuovo da uno noto; evita di riscoprire ogni volta le stesse cose |
| A5.8 | L1 | `HandlePowerKey=ignore`, con il tasto di accensione trattato come evento: l'agente decide, ad esempio uno spegnimento ordinato con snapshot. Lo spegnimento forzato con la pressione lunga resta all'hardware | Toglie H28 |
| A5.9 | L1 | `systemd-oomd` attivo con limiti per il gruppo dei lavori dell'agente, che proteggono i servizi dell'accesso | Un lavoro dell'agente che esaurisce la memoria non porta giù SSH |

**Da decidere nella sintesi:**
- quali eventi svegliano subito un agente e quali aspettano la prossima sessione;
- il limite di spesa per le sessioni aperte da un evento (A5.5).

---

## 6. L'harness dell'agente

L'harness è il programma che fa lavorare un modello come agente: il ciclo di ragionamento, gli strumenti, i
permessi, il contesto, le sessioni. La richiesta dell'utente è partire da Claude Code, così da usare subito gli
agenti Claude anche da remoto, senza costruire canali di comunicazione o app.

### 6.1 Cosa dicono le fonti ufficiali

Ricerca del 25/10/2026 sulla documentazione di Anthropic (code.claude.com) e sul repository
github.com/anthropics/claude-code:

| Tema | Fatto | Fonte |
|---|---|---|
| **Licenza** | Claude Code è **proprietario**: "© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service". Il codice non è open source e **un fork, cioè modificarlo e ridistribuirlo, non è permesso** | `LICENSE.md` del repository |
| **Claude Agent SDK** | Stesso ciclo dell'agente, stessi strumenti e stessa gestione del contesto di Claude Code, da usare dentro programmi propri in Python (`claude-agent-sdk`) o TypeScript (`@anthropic-ai/claude-agent-sdk`). Comprende hook, MCP, subagenti, permessi, sessioni. Licenza: termini commerciali di Anthropic | `agent-sdk/overview` |
| **Estendere senza fork** | Hook sugli eventi della sessione, che possono aggiungere contesto o bloccare un'azione; server MCP; plugin, che raccolgono hook, MCP e skill; skill; subagenti; stili di output; impostazioni gestite; modalità di permesso | `hooks`, `plugins`, `mcp` |
| **Senza interfaccia** | `claude -p "<richiesta>"`, uscita `json` o `stream-json`, ripresa di una sessione con `--continue` e `--resume`, strumenti permessi e modalità di permesso da riga di comando | `headless` |
| **Remote Control** | Collega una sessione di Claude Code che gira su una macchina a claude.ai/code o all'app Claude per telefono. File, strumenti e server MCP restano sulla macchina. Funziona anche su Linux; richiede un abbonamento Pro, Max, Team o Enterprise | `remote-control` |
| **Linux** | Binario nativo per x86_64 e ARM64, senza bisogno di Node.js; in alternativa il pacchetto npm (Node.js 22 o più). Distribuzioni elencate: Ubuntu, Debian, Alpine. **Arch non è nell'elenco** | `setup` |
| **Autenticazione senza persona** | Chiave API (`ANTHROPIC_API_KEY`); token OAuth di lunga durata da `claude setup-token` (`CLAUDE_CODE_OAUTH_TOKEN`); `apiKeyHelper`; Bedrock, Vertex, Foundry | `authentication` |

**Hook visti funzionare in questa sessione.** La governance del progetto è essa stessa un'estensione di
Claude Code fatta di hook:
- `SessionStart` e `UserPromptSubmit` iniettano regole e stato a ogni turno;
- `PreToolUse` nega gli strumenti fuori dalle regole, ad esempio durante il setup del ciclo;
- `PostToolUse` e `PostToolUseFailure` aggiungono istruzioni dopo un comando o un errore;
- `Stop` impedisce di chiudere un turno con la roadmap disallineata.

È autoprompting a livello di harness, già provato sul campo.

**Sulla Deck oggi:** x86_64, 8 thread, 14 GB di RAM quasi tutti liberi, git installato; Node.js non installato
ma disponibile nei repository ufficiali (26.12); nessuna installazione di Claude Code.

### 6.2 Dove vivono le sessioni

| Dove | Com'è | Adatto a |
|---|---|---|
| **Sul Mac** (oggi) | Claude Code sul Mac, la Deck raggiunta con SSH e `deck` | Sviluppare AgentDeck: repository, governance, documentazione stanno sul Mac |
| **Sulla Deck** | Claude Code installato sulla Deck, sessioni come unità di systemd, raggiungibili con Remote Control da claude.ai o dal telefono | Gestire AgentDeck dall'interno: l'agente vive nel sistema che governa; l'umano guarda e interviene da remoto senza app nostre |
| **Nel cloud** | Sessioni di Claude Code sul web, sopra un repository | Lavoro sul codice; non hanno accesso diretto al sistema della Deck |

### 6.3 Presupposti umani dell'harness

| # | Dove | Cosa presuppone | Effetto |
|---|---|---|---|
| H31 | Permessi | Una persona che approva le azioni una per una nell'interfaccia | In una sessione senza persona servono regole decise prima: permessi per strumento e i controlli del sistema (sezione 3) |
| H32 | Avvio | Una persona che apre la sessione e scrive la prima richiesta | L'agente non parte da solo: servono gli eventi (sezione 5) |
| H33 | Contesto | Un umano che spiega com'è fatto il sistema | Il sistema deve presentarsi da sé: istruzioni, stato, eventi |

### 6.4 Come il sistema alimenta l'harness

- **Interattività con MCP.** Le azioni di `deck` diventano strumenti dichiarati, con i parametri tipizzati
  presi dalle specifiche del protocollo. Le azioni distruttive restano in due passi: la prima chiamata
  restituisce anteprima e codice, la seconda conferma. Le schermate sono anche risorse leggibili.
- **Autoprompting con gli hook di AgentDeck**:
  - **all'inizio della sessione**, il briefing `deck inbox` (A5.4), insieme a invarianti e stato;
  - **prima di un comando grezzo**, la politica: dove esiste un'azione di `deck` la indica, e rifiuta ciò che
    toglierebbe l'accesso (INV-1);
  - **dopo un'azione**, le istruzioni di verifica;
  - **alla fine**, la registrazione nel registro delle azioni (A5.6).

  È lo schema che la governance usa già con successo.
- **Conoscenza:**
  - un `CLAUDE.md` di AgentDeck e skill per componente, generati da `docs/`, così la fonte resta una (INV-9);
  - subagenti per ruoli diversi: amministrazione, sviluppo, casa.
- **Identità e limiti:** ogni sessione è un agente con la sua identità (A3.2), gira senza privilegi e passa
  dal broker (A3.3); in senza interfaccia, strumenti e modalità di permesso sono fissati dal profilo
  dell'agente.

### 6.5 Proposte

| Id | Livello | Proposta | Perché |
|---|---|---|---|
| A6.1 | — | **Claude Code non modificato più un plugin di AgentDeck** (hook, MCP, skill, `CLAUDE.md`, impostazioni), che è la nostra "distribuzione" di Claude Code. **Decisione dell'utente (D1, 25/10): solo Claude Code, niente API di Claude**, quindi niente Agent SDK con chiave API e niente harness open source. Il fork di Claude Code non è permesso dalla licenza | Ottiene ciò che il fork avrebbe dato, cioè Claude come agente nativo di AgentDeck, restando dentro i termini, e riceve gli aggiornamenti di Claude Code senza doverli fondere |
| A6.2 | L2 | **`deck mcp`**: server MCP che serve il protocollo di `deck`, con strumenti, anteprime, conferme e risorse. In locale sulla Deck, e dal Mac con `ssh agentdeck deck mcp` | Interattività nativa nell'harness. Si costruisce sullo stesso motore di A2.3 |
| A6.3 | L2 | **Hook di AgentDeck** per Claude Code: briefing all'inizio, politica sui comandi grezzi, verifiche dopo le azioni, registro alla fine. Sono già sviluppati e provati nello schema della governance | Autoprompting nel punto in cui l'agente ragiona |
| A6.4 | L2 | **Claude Code sulla Deck**: binario nativo, sessioni come unità di systemd per l'utente dell'agente, raggiungibili con **Remote Control** da claude.ai o dal telefono | L'agente vive nel sistema; l'umano lo segue da remoto senza app nostre, come chiesto |
| A6.5 | L2 | **Sessioni avviate da un evento**, ed è anche l'agente interno: Claude Code senza interfaccia (`claude -p`, uscita `stream-json`, ripresa delle sessioni con `--resume`), con strumenti limitati e un tetto d'uso, lanciato dal raccoglitore di eventi (A5.5) come unità transitoria | La Deck risponde da sola agli eventi con lo stesso harness delle sessioni interattive |
| A6.6 | L1/L2 | **Credenziali dell'harness** con `deck secrets` (A3.6): il token di lunga durata dell'abbonamento (`claude setup-token`, `CLAUDE_CODE_OAUTH_TOKEN`), consegnato alle sessioni senza file in chiaro. Vanno verificate le condizioni d'uso dell'abbonamento per sessioni che partono da sole e i loro limiti d'uso | Nessuna credenziale in chiaro; una revoca per agente |

**Verifiche aperte:**
- che il binario nativo di Claude Code funzioni su Arch, che non è fra le distribuzioni elencate;
- se Remote Control funziona con l'autenticazione a chiave API o solo con l'abbonamento;
- che un server MCP raggiunto via SSH (stdio) funzioni nell'harness: rispetta la specifica, ma non è
  documentato esplicitamente.

**Da decidere nella sintesi:**
- **dove vive l'harness di gestione**: sulla Deck subito (A6.4), oppure dopo `deck mcp` e gli hook, provati
  prima dal Mac;
- **l'autenticazione** delle sessioni sulla Deck.

---

## 7. Sintesi: architettura proposta e decisioni

### 7.1 Cosa ha trovato lo studio

In sei strati, **33 presupposti umani** (H1-H33) e **49 proposte** (A1.1-A6.6). I presupposti si raggruppano
in cinque famiglie:

| Famiglia | Esempi | Cosa serve all'agente |
|---|---|---|
| **Qualcuno alla console** | Shell d'emergenza con root bloccato (H1), panic (H2), menu di GRUB (H4), password chieste alla console (H29) | Ripartire da soli, oppure restare raggiungibili via SSH anche quando qualcosa va storto |
| **Testo da leggere** | Output per terminale (H9), log in prosa (H27), errori in frasi (H12), notizie di Arch (H21) | Dati strutturati alla fonte: varlink, D-Bus, JSON, eventi con un codice |
| **Domande e conferme a voce** | Prompt interattivi (H11), approvazioni una per una (H31), polkit come dialogo (H16) | Regole decise prima, anteprime con codice di conferma, transazioni con ritorno automatico |
| **Un utente, una persona** | sudo per tutto (H15), un solo utente (H17), una chiave per sempre (H20) | Identità per agente e sessione; permessi per azione; traccia di chi ha fatto cosa |
| **Qualcuno che guarda quando vuole** | Monitoraggio a richiesta (H26), avvio della sessione da parte di una persona (H32), nessuna storia degli avvisi | Eventi in coda, briefing all'ingresso, risveglio dell'agente |

### 7.2 Gli schemi che tornano

Cinque schemi emergono in più strati e diventano i mattoni dell'architettura:

1. **Cambio con prova e ritorno automatico.** È già usato per il Wi-Fi (O4.T2) e per la rete di sicurezza SSH
   (O3.T4). Proposto per gli avvii (A1.6) e implicito negli aggiornamenti (O6). Un cambio rischioso si applica
   come prova; senza la conferma dell'agente entro un tempo dato, il sistema torna da solo allo stato di prima.
2. **Azione come schermata.** Dati, azioni tipizzate, anteprima e conferma: il protocollo di `deck`, da
   servire anche come varlink (A2.3) e MCP (A6.2).
3. **Evento, coda, briefing, risveglio** (A5.2-A5.5). Ciò che succede diventa un dato in coda; l'agente lo
   riceve all'ingresso, o viene svegliato.
4. **Stato voluto e stato reale** (A4.3, o A4.8). Il sistema sa cosa dovrebbe essere, e mostra e ripara la
   differenza.
5. **Identità con un broker** (A3.2-A3.3). L'agente chiede, il sistema decide per azione e registra.

E una regola che vale ovunque: **il testo esterno sta solo nei dati** (INV-4).

### 7.3 L'architettura in una pagina

```
   umano (in futuro)  ── canale effimero: Remote Control, pagine generate, notifiche ──┐
                                                                                     │
 ┌─ AGENTI ──────────────────────────────────────────────────────────────────────────┴─┐
 │  sessioni con identità (sviluppo, casa, interno), avviate da una persona o da un evento │
 ├─ HARNESS ──────────────────────────────────────────────────────────────────────────────┤
 │  Claude Code + plugin di AgentDeck (hook di autoprompting, deck mcp, skill, CLAUDE.md) │
 │  interattivo con Remote Control, oppure senza interfaccia (claude -p) per gli eventi  │
 ├─ INTERFACCE AGENTICHE ─────────────────────────────────────────────────────────────────┤
 │  deck (CLI)  ·  io.agentdeck.* (varlink)  ·  deck mcp (MCP)  — un solo protocollo     │
 ├─ SERVIZIO AGENTDECK (root) ────────────────────────────────────────────────────────────┤
 │  broker dei privilegi · stato voluto · eventi e coda · registro delle azioni ·        │
 │  transazioni con ritorno automatico · segreti (systemd-creds + TPM)                   │
 ├─ API NATIVE DEL SISTEMA ───────────────────────────────────────────────────────────────┤
 │  varlink e D-Bus di systemd, networkd, resolved, logind, iwd · JSON · /proc e /sys      │
 ├─ SISTEMA ──────────────────────────────────────────────────────────────────────────────┤
 │  Arch + systemd · Btrfs con snapshot e stati buoni · container nspawn per i carichi    │
 ├─ AVVIO ────────────────────────────────────────────────────────────────────────────────┤
 │  avvio di prova con conferma · watchdog · emergenza raggiungibile · (Secure Boot+TPM) │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

L'umano non ha un'interfaccia permanente. Quando servirà, la avrà effimera: segue o guida una sessione con
Remote Control, oppure l'agente genera una pagina quando c'è qualcosa da mostrare o da decidere. Lo schermo
della Deck resta un dettaglio (N9, N10 rimandate).

### 7.4 Le decisioni da prendere

Le decisioni che cambiano la forma del sistema, con le strade e la mia raccomandazione:

| Id | Decisione | Strade | Raccomandazione |
|---|---|---|---|
| D1 | **Harness** (A6.1, N21, N22) | **Deciso dall'utente il 25/10: Claude Code**, non modificato, con il plugin di AgentDeck; le sessioni autonome con `claude -p`. Niente API di Claude, niente Agent SDK con chiave API, niente harness open source. Il fork di Claude Code non è permesso dalla licenza (sezione 6) | — |
| D2 | **Avvio** (sezione 1) | GRUB con avvii di prova fatti da noi (A1.5-A1.6), oppure systemd-boot con kernel unificati, boot counting nativo, Secure Boot e TPM (A1.10, A1.11, A3.7) | Prima GRUB con A1.6, perché è veloce e protegge subito; systemd-boot quando arrivano i segreti sigillati |
| D3 | **Privilegi** (sezione 3) | L'agente resta root con le protezioni di `deck`, oppure lavora senza privilegi con il broker (A3.3) e polkit (A3.4) | Il broker, dopo il servizio di AgentDeck (A2.3), che ne è il presupposto |
| D4 | **Stato del sistema** (sezione 4) | Stato voluto dichiarativo dentro Arch (A4.3), oppure sistema a immagini (A4.8) | A4.3: tiene Arch com'è (INV-7) e risolve la deriva; A4.8 da rivalutare più avanti |
| D5 | **Interfaccia principale** (sezioni 2 e 6) | Comandi via SSH come oggi, oppure il servizio di AgentDeck (varlink) con MCP e la CLI come client | Il servizio con MCP: è ciò che rende AgentDeck nativo per gli agenti |
| D6 | **Dove vive l'harness di gestione** (A6.4) | Sulla Deck subito, oppure prima dal Mac con `deck mcp` e gli hook, poi sulla Deck | Prima dal Mac, poi sulla Deck, quando MCP e hook sono provati |
| D7 | **Risveglio** (A5.5, A6.5) | Con l'abbonamento, le sessioni che partono da sole sono una zona da chiarire nei termini (sezione 7.5). Strade: niente risveglio automatico, con gli eventi in coda letti all'ingresso; chiedere conferma ad Anthropic; chiave API solo per quelle sessioni | Per ora niente risveglio automatico: coda e briefing (A5.3-A5.4) danno già molto; chiedere conferma prima di costruire A5.5 |
| D8 | **Identità** (A3.2) | Quanti agenti e con quali ruoli all'inizio | Due: sviluppo (dal Mac) e gestione (sulla Deck) |
| D9 | **Regia dei comandi grezzi** (A2.4) | Sì o no; tocca la sessione SSH | Sì, con la rete di sicurezza SSH, dopo D5 |

**Interventi senza decisioni di forma.** Sono configurazione a basso rischio, e si possono fare subito con la
solita anteprima e le reti di sicurezza:
- avvio: A1.1, panic che riavvia; A1.2, watchdog hardware; A1.3, `/efi` senza blocco; A1.4, emergenza
  raggiungibile;
- interfacce: A2.1, ambiente delle sessioni;
- identità: A3.1, chiave limitata alla LAN e firewall; A3.8, audit;
- stato: A4.1, politica degli snapshot;
- eventi: A5.1, traccia separata; A5.2, `OnFailure=` globale; A5.8, tasto di accensione; A5.9, `systemd-oomd`.

### 7.4 bis Esito della revisione (25/10/2026)

Decisioni dell'utente nella revisione dello studio:

| Tema | Decisione |
|---|---|
| Impianto generale | Approvato in generale: architettura, mattoni e raccomandazioni delle decisioni D2-D9 restano la direzione. Ogni decisione si conferma quando arriva lo sviluppo che la riguarda |
| **D1 Harness** | Claude Code, niente API di Claude (sezione 7.5) |
| **Paradigma** | L'agente è uno strumento senza cognizione propria. **È il sistema operativo a guidarlo e a usarlo per il proprio funzionamento corretto**: in certi procedimenti il sistema fornisce dati, impone obblighi e dà istruzioni. Il modello è la governance, che guida Claude con hook, obblighi e stati |
| **Prompt interattivi** | Restano, perché sono autoprompting nativo dei programmi e non si può prevedere tutto. Cambia il trattamento di H11 e A2.4: invece di toglierli, un **adattatore** traduce in JSON per l'agente ciò che l'interfaccia mostra a un umano (schermo, domande, scelte, tabelle). Così si gestisce nativamente una moltitudine di programmi, senza strutturare ogni cosa su misura |
| **Profili dell'adattatore** | Li crea l'agente del sistema, dentro il sistema. Ad esempio, dopo l'installazione di un pacchetto, il sistema chiede all'agente di scrivere il profilo dei programmi nuovi |
| **Obblighi** | Si parte con obblighi solo di avviso, non bloccanti; la loro forza si decide con l'uso |
| **D6 e primo passo** | Lo sviluppo parte **inserendo Claude Code nel sistema**, sulla Deck. L'uso reale della chat e la configurazione diranno cosa serve, prima dell'adattatore e del resto |

**La schermata dell'adattatore**, proposta in revisione e da precisare con l'uso. Resta dentro il protocollo di
`deck`, più il campo nuovo `obligations`:
- `data.session`: programma, stato (`running`, `waiting_input`, `exited`, `stalled`), durata;
- `data.terminal`: righe visibili, righe nuove, cursore;
- `data.question`: testo originale, tipo (`confirm`, `choice`, `text`, `secret`, `menu`, `pager`, `unknown`),
  opzioni, predefinito, origine del riconoscimento;
- `data.parsed`: ciò che il profilo estrae;
- `actions`: rispondere, anche con un riferimento a un segreto, scegliere, premere un tasto, aspettare,
  interrompere;
- `prompt` e `obligations`: istruzioni e doveri scritti dal sistema, mai dal programma (INV-4).

### 7.5 Harness: perché Claude Code senza modifiche

- **Un fork non si può fare, nemmeno in privato.** La licenza di Claude Code non parla di vendita: dice
  "All rights reserved", quindi modificarne il codice e farne girare una copia modificata non è concesso, che
  il progetto sia commerciale o no. Una copia modificata userebbe comunque l'account dell'utente, con il rischio
  di violare i termini.
- **Non serve.** Ciò che un fork avrebbe dato si ottiene con le estensioni previste da Anthropic:
  - il comportamento dell'agente: istruzioni, regole e contesto iniettati dagli hook a ogni turno, come fa già
    la governance;
  - gli strumenti: `deck mcp`;
  - la conoscenza: `CLAUDE.md` e skill;
  - i permessi: le impostazioni e gli hook che bloccano;
  - il lavoro autonomo: `claude -p` e la ripresa delle sessioni;
  - il controllo a distanza: Remote Control.

  Resta fuori solo l'interfaccia del terminale, che per AgentDeck non conta.
- **Si studia dall'esterno**: comportamento, impostazioni, formati di uscita e ciclo degli hook sono documentati,
  e sono quanto basta per integrarlo a fondo.

**I termini, verificati il 25/10/2026 su fonti primarie:**

| Fonte | Cosa dice |
|---|---|
| `LICENSE.md` di Claude Code | "© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service." |
| Consumer Terms (Free, Pro, Max), anthropic.com/legal/consumer-terms | Vietato "decompile, reverse engineer, disassemble, or otherwise reduce our Services to human-readable form", salvo dove la legge applicabile lo impedisce. Vietato l'accesso automatizzato "except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it" |
| Commercial Terms (API, Team, Enterprise), anthropic.com/legal/commercial-terms | Vietato "reverse engineer or duplicate the Services" |
| Legale e conformità di Claude Code, code.claude.com/docs/en/legal-and-compliance | Il login OAuth dell'abbonamento è pensato "to support ordinary use of Claude Code and other native Anthropic applications"; per chi sviluppa con l'Agent SDK serve una chiave API; "The Claude Code binary must not be modified" |

Ne seguono tre fatti:
- **Modificare Claude Code è escluso**, anche in privato: non c'è un'eccezione per l'uso non commerciale.
- **Le sessioni interattive con l'abbonamento**, comprese quelle seguite con Remote Control, sono l'uso
  previsto.
- **Le sessioni avviate da sole su un evento** (`claude -p`, A6.5) con l'abbonamento sono una **zona da
  chiarire**: è una funzione di Claude Code stesso, ma i termini dell'abbonamento escludono l'accesso
  automatizzato salvo permesso esplicito o chiave API.

  Prima di costruire A5.5 e A6.5 serve una decisione. Le strade:
  1. limitarsi a sessioni interattive e seguite da remoto, con la coda di eventi letta all'ingresso (A5.4);
  2. chiedere conferma ad Anthropic;
  3. accettare per le sole sessioni automatiche una chiave API, che però hai escluso.

La verifica ha confrontato anche gli harness open source che si possono forkare (OpenCode MIT, Aider e Goose
Apache-2.0, Cline Apache-2.0, OpenHands MIT). Funzionano con Claude solo con una chiave API, che hai escluso:
restano fuori.

### 7.6 Roadmap proposta

Da decidere in revisione. È l'ordine che segue dalle raccomandazioni:

1. **Ciclo 04, fondamenta autonome:**
   - la Deck riparte da sola e resta raggiungibile: gli interventi di configurazione elencati sopra, gli avvii
     di prova (A1.6) e `deck boot` (A1.7);
   - la politica degli snapshot e gli stati buoni (A4.1, A4.2);
   - gli eventi in coda e il briefing (A5.2-A5.4, A5.6).
2. **Ciclo 05, AgentDeck nativo per gli agenti:**
   - il servizio di AgentDeck con il protocollo su varlink (A2.3);
   - le API native al posto del testo (A2.2, A2.7);
   - `deck mcp` (A6.2) e il plugin con gli hook (A6.3), provati dal Mac;
   - `deck secrets` (A3.6).
3. **Ciclo 06, l'agente vive sulla Deck:**
   - l'harness sulla Deck con Remote Control (A6.4);
   - identità e broker dei privilegi (A3.2-A3.4);
   - le sessioni avviate da un evento (A5.5, A6.5), solo se la decisione D7 e i termini lo permettono;
   - lo stato voluto (A4.3).
4. **In parallelo, quando arriva:** la prova di `deck update` con un aggiornamento vero (O9.T1).
