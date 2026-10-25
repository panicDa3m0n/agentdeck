# Hardware della Deck

Inventario letto dalla Deck il 25 ottobre 2026 (sistema live di Arch, poi sistema installato).
Indice: [README.md](README.md).

## Componenti

| Componente | Dettaglio | Note |
|---|---|---|
| Modello | Steam Deck **LCD**, codice DMI `Jupiter`, BIOS F7A0120 | |
| APU | AMD Custom APU 0405 (Van Gogh), 8 thread, fino a 2,8 GHz | |
| RAM | 16 GB (circa 14 GiB visibili al sistema) | Una parte è riservata alla GPU |
| Disco di sistema | NVMe **WD PC SN740 SDDPTQE-2T00, 2 TB** | Sostituito rispetto all'originale; SMART OK, praticamente nuovo |
| microSD | 1 TB (928 GB utili) | **Non toccata** (decisione del 25/10): contiene ancora un layout da Windows (EFI, MSR, NTFS) |
| Wi-Fi | Realtek RTL8822CE (802.11ac) | Collegata ai 5 GHz (5500 MHz, segnale circa -26 dBm, 585 Mbit/s in trasmissione contro i 144 dei 2,4 GHz) dal 25/10 con `deck network prefer_5ghz`. Il router di casa trasmette i 5 GHz come **rete distinta**, "… - 5Ghz", con la stessa password; la rete a 2,4 GHz resta come riserva. IP invariato |
| Schermo | eDP 800×1280, montato in verticale | La console Linux appare già in orizzontale |
| Ventola | Gestita dal firmware della Deck | Linux non ne legge i giri: nessun sensore `fan` in hwmon |
| Batteria | `BAT1`, alimentatore `ACAD` | La Deck resta sempre collegata alla corrente |
| USB | Una sola porta USB-C | Chiavetta e alimentazione passano da un hub |

Temperatura a riposo: circa 43-44 °C (APU e NVMe).

## Avvio (UEFI)

- Ordine di avvio: prima **GRUB** dall'NVMe, poi le voci generiche del firmware.
- Una copia di GRUB sta anche nel percorso di riserva `\EFI\BOOT\BOOTX64.EFI`, se il firmware perdesse la
  voce di avvio.
- **Menu di avvio del firmware:** a Deck spenta, tenere premuto **Volume giù** e premere **Accensione**.
  Serve per avviare la chiavetta di recupero ([chiavetta-live.md](chiavetta-live.md)).

## Limiti e lezioni

- **Hub USB-C e alimentazione:** staccando l'alimentatore dall'hub, l'hub rinegozia la corrente e scollega
  per un attimo **tutti** i dispositivi collegati. Durante l'installazione questo ha fatto perdere la
  chiavetta al sistema live. Mentre si lavora dalla chiavetta non si toccano i cavi.
- **Cavo USB-C verso il Mac:** Mac e Deck sono entrambi "host" USB, quindi il cavo non crea un collegamento
  dati. Il BIOS della Deck dovrebbe avere un'opzione "dual role" per la modalità periferica: è una
  direzione da valutare (vedi [../PRINCIPI.md](../PRINCIPI.md)).

## Da sistemare più avanti

- Controllo della ventola e lettura dei giri.
- Limite di carica della batteria, visto che la Deck resta sempre in carica.
