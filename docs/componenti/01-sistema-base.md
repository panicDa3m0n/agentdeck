# 01 Sistema base e avvio: lo scheletro

**Stato:** attivo. L'avvio robusto e il safe mode sono previsti. Indice: [README.md](README.md).

## Scopo

È la macchina e il sistema su cui vive tutto il resto: la Steam Deck LCD con Arch Linux, i dischi in Btrfs, l'avvio
con GRUB e la chiavetta di recupero. È lo strato dove un errore costa di più, perché nessuno è alla macchina.

## Come funziona oggi

- **Hardware:** Steam Deck LCD (Valve Jupiter, APU AMD a 8 thread, 16 GB, NVMe da 2 TB), sempre in carica, ventola
  gestita dal firmware ([../hardware.md](../hardware.md)).
- **Disco:** EFI da 2 GiB su `/efi`, più una partizione Btrfs con i subvolumi `@` (sistema), `@home`, `@log`, `@pkg`,
  `@snapshots` e `@servizi`. Compressione `zstd:1`, subvolumi per nome in `fstab`
  ([../installazione.md](../installazione.md)).
- **Sistema:** Arch Linux (INV-7). Kernel `linux` in uso (7.2.x) e `linux-lts` di riserva; `iwd`,
  `systemd-networkd`, `systemd-resolved`, OpenSSH, zram, sudo senza password per `agent`, root bloccato.
- **Avvio:** GRUB con `grub-btrfs`: dal menu si può partire da uno snapshot.
- **Recupero:** una chiavetta live con Wi-Fi e SSH automatici, preparata dal Mac
  ([../chiavetta-live.md](../chiavetta-live.md)).
- **Installazione a fasi:** [../../install/install.sh](../../install/install.sh) e
  [../../install/post-install.sh](../../install/post-install.sh).

## Comandi collegati

`deck status` (macchina, sensori, batteria, disco, servizi); `deck update` per kernel e pacchetti (componente 03).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Arch sulla Deck con Btrfs, snapshot avviabili, accesso con chiave | cicli 01-02 (O1) | ✔ 25/10/2026 |
| Chiavetta live di recupero | O1 | ✔ |
| Mappa dell'avvio e del ripristino | O8.T1 | ✔ studio in [../architettura.md](../architettura.md), sezione 1 |
| Riavvio da solo dopo un panic (`kernel.panic`) | A1.1 | ✖ previsto |
| Watchdog hardware (`sp5100_tco`) | A1.2 | ✖ previsto |
| `/efi` con `nofail`, così non blocca l'avvio | A1.3 | ✖ previsto |
| Emergenza raggiungibile via SSH al posto della shell che aspetta un umano | A1.4 | ✖ previsto |
| GRUB con scelta del prossimo avvio a distanza | A1.5 | ✖ previsto |
| Avvio di prova con conferma e ritorno automatico | A1.6 (decisione D2: prima GRUB con A1.6) | ✖ previsto |
| `deck boot`: storia degli avvii e prossimo avvio con anteprima | A1.7 | ✖ previsto |
| `soft-reboot` per i cambi solo in spazio utente | A1.8 | ✖ previsto |
| systemd-boot con kernel unificati e Secure Boot | A1.10, A1.11, A3.7 | ✖ previsto, più avanti |
| **Safe mode**: un sistema quasi nudo raggiungibile via SSH per ripristini e riparazioni | piano punto 2-bis | ✖ previsto, prima dei backup |

## Issue aperte

- Un riavvio non c'è modo di controllarlo a distanza: se il kernel nuovo non parte, oggi serve qualcuno alla Deck
  o la chiavetta. È il rischio più grosso del sistema. Il 30/10 l'agente interno ha riavviato da solo dopo un
  aggiornamento del kernel `linux-lts`: è andata bene, ma senza rete di sicurezza (componente 11).
- Velocità della ventola non leggibile (avviso `FAN_UNREADABLE`, informativo).
- Nessun limite di carica della batteria, sempre al 98-100% ([../hardware.md](../hardware.md)).

## Obiettivi tecnici

1. A1.1-A1.3 (configurazione, livello L1): pochi minuti e grande guadagno.
2. A1.6 con A1.4: avvio di prova con conferma e ritorno automatico, ed emergenza raggiungibile.
3. Safe mode (punto 2-bis) da progettare insieme ad A1.4.
