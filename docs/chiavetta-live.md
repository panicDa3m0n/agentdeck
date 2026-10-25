# Chiavetta live

Una chiavetta USB con l'ISO ufficiale di Arch che, all'avvio sulla Deck, si collega da sola al Wi-Fi e
abilita SSH con la chiave dell'agente. Non tocca il disco interno. Serve per installare il sistema
([installazione.md](installazione.md)) e per recuperarlo se la Deck non fosse più raggiungibile
([accesso.md](accesso.md)).

Codice:
- [../live/prepare-stick.sh](../live/prepare-stick.sh): prepara la chiavetta dal Mac.
- [../live/live-setup.sh](../live/live-setup.sh): gira sulla Deck all'avvio della chiavetta.
- [../live/authorized_keys](../live/authorized_keys): chiave pubblica dell'agente che viene copiata sulla chiavetta.

Indice: [README.md](README.md).

## Preparare la chiavetta (dal Mac)

1. Scaricare l'ISO ufficiale in `cache/` e verificarne il checksum: il percorso e lo SHA-256 attesi sono in
   cima a `prepare-stick.sh` (oggi `archlinux-2026.10.01-x86_64.iso`).
2. Compilare `secrets/wifi.env` (escluso da git). I valori vanno scritti subito dopo `=`, senza virgolette:
   ```
   WIFI_SSID=nome della rete
   WIFI_PASS=password
   ```
3. Individuare la chiavetta con `diskutil list external physical`, poi provare i controlli senza scrivere
   nulla:
   ```bash
   DRY_RUN=1 live/prepare-stick.sh disk9
   ```
4. Scrivere la chiavetta (**cancella il disco indicato**):
   ```bash
   live/prepare-stick.sh disk9
   ```

`prepare-stick.sh` rifiuta i dischi interni, quelli non USB e quelli di dimensione non plausibile per una
chiavetta (meno di 4 GB o più di 256 GB). Poi verifica il checksum dell'ISO, formatta la chiavetta in FAT32
con etichetta `ARCH_202610`, copia il contenuto dell'ISO e aggiunge la cartella `agent/` con
`live-setup.sh`, la chiave pubblica e `wifi.env`.

## Usarla sulla Deck

1. Deck spenta, chiavetta collegata (tramite hub o adattatore USB-C).
2. Tenere premuto **Volume giù** e premere **Accensione**, poi scegliere la voce USB ("EFI USB Device").
3. Dopo circa un minuto sullo schermo compare **PRONTA** con l'IP.
4. Dal Mac: `ssh -i ~/.ssh/id_ed25519_steamdeck root@agentdeck-live.local`, oppure con l'IP mostrato.

Quando la Deck è già accesa e raggiungibile, si può riavviare direttamente sulla chiavetta senza toccarla,
impostando `BootNext` sulla voce USB (`efibootmgr -n <numero>`).

## Come funziona

- **Avvio per etichetta:** la voce di boot dell'ISO cerca il disco per UUID (`archisosearchuuid`), che una
  chiavetta FAT32 non può avere. `prepare-stick.sh` lo sostituisce con `archisolabel=ARCH_202610`.
- **Script automatico:** l'ISO ufficiale esegue su tty1 il file indicato dal parametro di boot `script=`
  (meccanismo `.automated_script.sh` di archiso). La voce di boot punta a
  `/run/archiso/bootmnt/agent/live-setup.sh`.
- **`copytoram=n`:** con molta RAM archiso copierebbe il sistema in memoria e smonterebbe la chiavetta
  prima che lo script parta, rendendolo irraggiungibile. Per questo la chiavetta resta montata.
- **`live-setup.sh`:**
  - installa la chiave dell'agente per root;
  - imposta il nome `agentdeck-live` con mDNS;
  - si collega al Wi-Fi con `iwctl`, riprovando fino a 10 volte;
  - avvia SSH e mostra l'IP a schermo.

  Il log resta in `/root/live-setup.log`.

## Attenzioni

- La chiavetta contiene la **password del Wi-Fi in chiaro**: va conservata in un posto sicuro.
- Con `copytoram=n` il sistema live legge i programmi dalla chiavetta: se la chiavetta si scollega anche
  per un attimo (per esempio staccando l'alimentazione dall'hub), quasi tutti i comandi smettono di
  funzionare e serve un riavvio. Vedi [hardware.md](hardware.md).
- Per aggiornare l'ISO cambiano tre valori in cima a `prepare-stick.sh`: percorso, SHA-256 ed etichetta.
