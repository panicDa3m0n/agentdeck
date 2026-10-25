# Changelog

Storia delle versioni di AgentDeck. Schema MAJOR.MINOR.PATCH gestito dalla governance: il terzo numero
sale a ogni task completata, il secondo a ogni ciclo chiuso, il primo solo con il sì dell'utente.
Ogni versione è pubblicata su https://github.com/panicDa3m0n/agentdeck con il tag `v<versione>`.

## 0.1.3 — 2026-10-25

Ciclo 01, task O1.T3: comandi di base attesi dagli agenti.

- Installato `inetutils` sulla Deck: ora `hostname` è disponibile e restituisce `agentdeck`.
- Snapshot automatici prima e dopo l'installazione (snap-pac).
- Pacchetto aggiunto all'elenco di `install/install.sh`.

## 0.1.2 — 2026-10-25

Ciclo 01, task O1.T2: IP stabile della Deck sulla rete di casa.

- `SendRelease=no` nella configurazione DHCP (Wi-Fi e cavo): allo spegnimento la Deck non restituisce
  l'indirizzo e il router le riassegna lo stesso. Prima ogni riavvio portava all'IP successivo.
- Verificato con due riavvii consecutivi: IP sempre `192.168.1.49`, `ssh agentdeck` al primo tentativo.
- Correzione riportata in `install/install.sh`.

## 0.1.1 — 2026-10-25

Ciclo 01, task O1.T1: identità git personale e remote privato su GitHub.

- Identità git personale (Davide, davideditrani94@gmail.com) impostata solo per questo repository;
  autore corretto anche sul primo commit.
- Repository privato `panicDa3m0n/agentdeck` con `main` e tag di versione.
- Credential helper locale: il repository pubblica sempre come `panicDa3m0n`, qualunque account `gh` sia attivo.

## 0.1.0 — 2026-10-25

Installazione base e governance del progetto.

- Principi del progetto (PRINCIPI.md).
- Chiavetta live di Arch con Wi-Fi e SSH automatici (`live/`).
- Installazione di Arch sulla Steam Deck a fasi (`install/`): Btrfs con snapshot, GRUB + grub-btrfs,
  utente `agent` con accesso solo via chiave.
- Behaviour Governance: dossier, 10 invarianti, roadmap del ciclo 01.
