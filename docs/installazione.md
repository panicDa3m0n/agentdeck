# Installazione di Arch sulla Deck

L'installazione si fa a fasi, via SSH, dal sistema live avviato con la chiavetta
([chiavetta-live.md](chiavetta-live.md)). Ogni fase si lancia separatamente, così si può controllare il
risultato prima di passare alla successiva. L'unica fase distruttiva chiede una conferma esplicita.

Codice:
- [../install/install.sh](../install/install.sh): le fasi di installazione, da root sul sistema live.
- [../install/post-install.sh](../install/post-install.sh): rifinitura dopo il primo avvio, come `agent`.
- [../install/claude-code.sh](../install/claude-code.sh): Claude Code per l'utente `agent`, con verifica della firma ([claude-code.md](claude-code.md)).
- [../install/remote-access.sh](../install/remote-access.sh): accesso da fuori casa, con sshguard e Tailscale spento ([accesso.md](accesso.md)).
- [../servizi/install-servizi.sh](../servizi/install-servizi.sh): l'area dei servizi ospitati, un passo a sé ([servizi.md](servizi.md)).

Indice: [README.md](README.md).

## Come si esegue

```bash
scp install/install.sh root@agentdeck-live.local:/root/install.sh
ssh root@agentdeck-live.local 'bash /root/install.sh check'
ssh root@agentdeck-live.local 'CONFIRM=nvme0n1 bash /root/install.sh disk'
ssh root@agentdeck-live.local 'bash /root/install.sh base'
ssh root@agentdeck-live.local 'bash /root/install.sh config'
ssh root@agentdeck-live.local 'bash /root/install.sh boot'
ssh root@agentdeck-live.local 'bash /root/install.sh verify'
ssh root@agentdeck-live.local 'bash /root/install.sh finish && systemctl reboot'
```

La fase `base` scarica i pacchetti per diversi minuti: conviene lanciarla staccata dalla sessione
(`setsid nohup … > /root/base.log`) e seguirne il log, così una caduta della connessione non la interrompe.

Dopo il primo avvio, verificato che `ssh agentdeck` funziona:

```bash
ssh agentdeck 'bash -s' < install/post-install.sh
```

Poi `deck` ([deck.md](deck.md), `deck/install.sh`) e Claude Code:

```bash
scp install/claude-code.sh agentdeck:/tmp/ && ssh agentdeck 'bash /tmp/claude-code.sh latest'
```

Infine l'accesso da fuori casa, dal Mac. Serve anche la regola di port forwarding sul router, descritta in
[accesso.md](accesso.md):

```bash
bash install/remote-access.sh
```

L'area dei servizi ospitati, se serve, è un passo a sé, perché tocca fstab e i subvolumi
([servizi.md](servizi.md), "Uso").

## Le fasi

| Fase | Cosa fa | Distruttiva |
|---|---|---|
| `check` | Verifica che sia il sistema live su una Steam Deck LCD in UEFI, che il disco sia il WD SN740 atteso, che ci sia un profilo Wi-Fi da copiare e internet | No |
| `disk` | Cancella l'NVMe (wipefs, TRIM completo, nuova tabella GPT), crea partizioni, filesystem e subvolumi | **Sì**, richiede `CONFIRM=nvme0n1` |
| `base` | Installa i pacchetti con `pacstrap` e genera `fstab` senza `subvolid` | No |
| `config` | Lingua, fuso, nome, utente `agent`, SSH, rete, zram, niente sospensione | No |
| `boot` | initramfs, GRUB, Snapper e primo snapshot, ordine di avvio UEFI | No |
| `verify` | Ricontrolla tutto in sola lettura | No |
| `finish` | Collega `resolv.conf` a systemd-resolved e smonta | No |

## Risultato

### Disco

| Partizione | Dimensione | Filesystem | Montata in |
|---|---|---|---|
| `nvme0n1p1` | 2 GiB | FAT32, etichetta `EFI` | `/efi` |
| `nvme0n1p2` | resto (circa 1,86 TiB) | Btrfs, etichetta `agentdeck` | subvolumi sotto |

| Subvolume | Montato in | Perché separato |
|---|---|---|
| `@` | `/` | Il sistema: è quello che gli snapshot salvano e ripristinano |
| `@home` | `/home` | I dati dell'utente non tornano indietro con un rollback |
| `@log` | `/var/log` | I log restano anche dopo un rollback, per capire cosa è successo |
| `@pkg` | `/var/cache/pacman/pkg` | La cache dei pacchetti non riempie gli snapshot |
| `@snapshots` | `/.snapshots` | Gli snapshot di Snapper |

Opzioni di mount: `noatime,compress=zstd:1`. In `fstab` i subvolumi sono indicati per nome e non per id,
perché dopo un rollback l'id cambia.

### Sistema

- **Pacchetti:**
  - base: `linux` e `linux-lts`, firmware, `amd-ucode`;
  - disco e avvio: Btrfs, GRUB, `grub-btrfs`, Snapper e `snap-pac`;
  - rete e accesso: `iwd`, OpenSSH, sudo;
  - memoria e console: zram, font Terminus;
  - strumenti: `base-devel`, git, vim, jq, rsync, htop, smartmontools, `inetutils` (per `hostname`).
- **Lingua e console:** sistema in inglese (`en_US.UTF-8`), fuso Europe/Rome, tastiera della console `it`, font `ter-124b`.
- **Nome:** `agentdeck`.
- **Utente `agent`:** gruppo `wheel`, sudo senza password (`/etc/sudoers.d/10-agent`), accesso solo con chiave. Root bloccato.
- **SSH** (`/etc/ssh/sshd_config.d/10-agentdeck.conf`): niente password. All'installazione root è ammesso con chiave come riserva per il primo avvio; `post-install.sh` lo disattiva.
- **Rete:**
  - `iwd` per il Wi-Fi, con il profilo copiato dal sistema live e la preferenza per i 5 GHz
    (`/etc/iwd/main.conf`, `[Rank] BandModifier5GHz=1.5`);
  - `systemd-networkd` per il DHCP, `systemd-resolved` per il DNS e mDNS (`agentdeck.local`);
  - LLMNR spento (`/etc/systemd/resolved.conf.d/20-agentdeck-llmnr.conf`): non serve e ascolterebbe sulla
    porta 5355 di tutta la LAN. Sono le stesse impostazioni di `deck network llmnr_off` e `prefer_5ghz`
    ([deck.md](deck.md)). Il profilo della rete a 5 GHz di casa invece non viene copiato: dopo una
    reinstallazione lo crea `deck network prefer_5ghz`;
  - `SendRelease=no` nei file `.network`, così il router riassegna sempre lo stesso IP;
  - un file per il cavo (metrica 100) e uno per il Wi-Fi (metrica 600).
- **Memoria e alimentazione:** zram pari a metà della RAM con zstd; sospensione e ibernazione disattivate (`systemctl mask`).

### Avvio e snapshot

- **initramfs classico basato su udev** (`/etc/mkinitcpio.conf.d/10-agentdeck.conf`) con il hook
  `grub-btrfs-overlayfs`. Quel hook, che permette di avviare gli snapshot in sola lettura, non funziona con
  l'initramfs basato su systemd.
- **GRUB:**
  - attesa del menu 2 secondi;
  - `GRUB_TOP_LEVEL="/boot/vmlinuz-linux"`, perché altrimenti GRUB sceglie `linux-lts` come predefinito;
  - installato sia come voce UEFI sia nel percorso di riserva.
- **Snapper:**
  - snapshot automatici prima e dopo ogni operazione di pacman (`snap-pac`);
  - snapshot a orario (5 orari, 7 giornalieri) e al massimo 20 snapshot numerati;
  - il menu di GRUB si aggiorna da solo (`grub-btrfsd`).
- La voce UEFI di Windows viene rimossa.

## Lezioni dall'installazione del 25/10

- Al primo avvio partiva il kernel LTS: corretto con `GRUB_TOP_LEVEL`, ora anche in `install.sh`.
- L'IP cambiava a ogni riavvio (`.47`, `.48`, …): corretto con `SendRelease=no`.
- Il reset dell'hub USB ha interrotto la prima installazione: vedi [hardware.md](hardware.md).
- Il primo avvio dura circa 20 secondi: 7 di firmware, 4 di GRUB, 6,6 di kernel e 2,6 di sistema.
