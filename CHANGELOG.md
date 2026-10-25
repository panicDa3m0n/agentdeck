# Changelog

Storia delle versioni di AgentDeck. Schema MAJOR.MINOR.PATCH gestito dalla governance: il terzo numero
sale a ogni task completata, il secondo a ogni ciclo chiuso, il primo solo con il sì dell'utente.
Ogni versione è pubblicata su https://github.com/panicDa3m0n/agentdeck con il tag `v<versione>`.

## 0.1.7 — 2026-10-25

Ciclo 01, task O2.T2: motore `deck` e installazione sulla Deck.

- `deck` implementa il protocollo v1:
  - schermate validate prima di ogni risposta;
  - canale istruzioni protetto: solo testo `SysText` con valori validati;
  - navigazione per indirizzi, parametri tipizzati;
  - conferme con codice (5 minuti, una volta sola);
  - errori strutturati con vie d'uscita.
- Componenti: `/` (schermata principale) e `/protocol` (il protocollo descritto all'agente).
- 22 test (conformità, iniezione nel canale istruzioni, parametri, conferme, guasti), verdi sul Mac e
  sulla Deck; una chiamata dura circa 0,09 secondi sulla Deck.
- Installazione ripetibile con `deck/install.sh` in `/opt/agentdeck`; documentazione in `docs/deck.md`.

## 0.1.6 — 2026-10-25

Ciclo 01, task O2.T1: specifica del protocollo di schermata e autoprompting.

- `docs/protocollo.md`, approvato: ogni risposta di `deck` è una schermata JSON con dati, azioni,
  navigazione, avvisi, errori, conferme con anteprima e istruzioni per l'agente (autoprompting).
- Regole di sicurezza del canale istruzioni (INV-4) e 8 esempi con dati reali della Deck.
- Decisioni: Python 3 con la sola libreria standard; testi per l'agente in inglese.

## 0.1.5 — 2026-10-25

Ciclo 01, task O1.T5: accesso SSH affidabile dal Mac.

- `ssh agentdeck` punta all'IP stabile `192.168.1.49` invece che al nome `agentdeck.local`, che dal Mac a
  volte non si risolve. Il nome resta disponibile come `ssh agentdeck-mdns`.
- `HostKeyAlias agentdeck`: l'identità della Deck si controlla sotto un solo nome, qualunque indirizzo si usi.
- Verificato con 10 collegamenti consecutivi riusciti al primo tentativo; `docs/accesso.md` aggiornato.
- Contatore delle versioni della governance riallineato: era rimasto indietro di una versione.

## 0.1.4 — 2026-10-25

Ciclo 01, task O1.T4: documentazione di base, indicizzata e collegata al codice.

- `README.md` del progetto e indice `docs/README.md`.
- Documenti per argomento: hardware, chiavetta live, installazione, accesso alla Deck, sviluppo
  (repository, versioni, pubblicazione, governance).
- `PRINCIPI.md`: principio del livello di intervento (INV-10) e decisioni del 25/10.
- Ogni script in `live/` e `install/` rimanda al suo documento, e ogni documento agli script.

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
