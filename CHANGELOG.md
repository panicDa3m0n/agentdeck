# Changelog

Storia delle versioni di AgentDeck. Schema MAJOR.MINOR.PATCH gestito dalla governance: il terzo numero
sale a ogni task completata, il secondo a ogni ciclo chiuso, il primo solo con il sì dell'utente.
Ogni versione è pubblicata su https://github.com/panicDa3m0n/agentdeck con il tag `v<versione>`.

## 0.2.3 — 2026-10-25

Ciclo 02, task O5.T1: componente `deck service`.

- `deck service` elenca i servizi di systemd come `systemctl list-units --all`, con abilitazione, conteggi e
  servizi falliti; `deck service show name=…` ne mostra il dettaglio.
- Azioni `start`, `stop`, `restart`, `enable`, `disable`:
  - `stop`, `restart` e `disable` con anteprima e conferma;
  - snapshot prima di `enable` e `disable`;
  - dopo ogni azione lo stato viene riletto e confrontato con quello atteso.
- Protezione dell'accesso: `stop` e `disable` rifiutati per `sshd`, `systemd-networkd`, `iwd`,
  `systemd-resolved` e `dbus-broker` (da cui dipende iwd) e per ciò che richiedono; `restart` di sshd solo
  con la configurazione valida.
- L'avviso `SERVICES_FAILED` di `deck status` ora rimanda a `/service`.
- Controllo dal vivo 28 su 28, con un servizio di prova creato e tolto; 122 test.

## 0.2.2 — 2026-10-25

Ciclo 02, task O4.T2: azioni di rete con anteprima e rete di sicurezza.

- `deck network llmnr_off` (con anteprima, snapshot e verifica di DNS e mDNS) e `llmnr_on` per tornare
  indietro. LLMNR è spento sulla Deck: la porta 5355 non è più in ascolto sulla LAN.
- `deck network prefer_5ghz` passa alla rete a 5 GHz dello stesso router, copiando sulla Deck la password
  della rete attuale senza mostrarla. Il cambio gira in un'unità a parte e torna da solo alla rete di prima
  senza un indirizzo entro 1 minuto o senza `deck network keep_5ghz` entro 3 minuti.
- Provato sulla Deck:
  - ritorno automatico senza conferma, 5 secondi dopo la scadenza;
  - cambio confermato, con riavvio di iwd e riavvio della Deck: resta sui 5 GHz, IP .49, `ssh agentdeck` ok;
  - 585 Mbit/s in trasmissione contro 144.
- Trovato e corretto: iwd si collega solo a reti viste da una sua scansione (P12). Le reti nascoste del
  router non contano più come reti sorelle.
- `install/install.sh` spegne LLMNR e dà a iwd la preferenza per i 5 GHz. Controllo dal vivo 11 su 11;
  100 test.

## 0.2.1 — 2026-10-25

Ciclo 02, task O4.T1: componente `deck network` (riprende N8).

- Interfacce, Wi-Fi collegato e reti visibili per banda: cache del kernel nella schermata, scansione fresca
  con `deck network scan` (circa 5 secondi).
- Reti sorelle dello stesso router; DNS, mDNS e LLMNR da `resolvectl`; porte in ascolto.
- Gli avvisi `WIFI_BAND_2G` e `LLMNR_LISTENING`, in `deck status` e `deck network`, puntano alle azioni di
  `/network`, che restano non disponibili fino a O4.T2.
- Scoperto: i 5 GHz di casa sono una rete distinta, "… - 5Ghz". Controllo dal vivo: 11 valori su 11; 80 test.

## 0.2.0 — 2026-10-25

Chiusura del ciclo 01, "Prima interfaccia agentica: protocollo, stato e snapshot": 3 obiettivi, 12 task,
nessun blocco. Roadmap archiviata in `.claude/workflow/roadmaps/`. Aperto il ciclo 02, "La Deck come server
gestito dall'agente: rete, servizi, aggiornamenti, schermo".

- O1: base operativa affidabile.
  - Repository privato con identità personale e una versione pubblicata per ogni task.
  - IP stabile e accesso SSH al primo tentativo.
  - Documentazione per argomento.
- O2: protocollo dell'interfaccia agentica approvato (`docs/protocollo.md`) e motore `deck` sulla Deck.
- O3: `deck status`, `deck snapshot` con rollback provato, schermo della Deck con comandi e risposte.

## 0.1.12 — 2026-10-25

Ciclo 01, task O3.T3: rollback con anteprima e conferma.

- `deck snapshot rollback id=N` mostra prima un'anteprima: pacchetti rimossi, che tornano o che cambiano
  versione, controllo dell'accesso SSH e della versione di GRUB nello snapshot di destinazione.
- Con il codice di conferma: salva lo stato attuale come snapshot, sostituisce il subvolume `@` con una copia
  dello snapshot (rimettendo subito tutto com'era se un passo fallisce) e riavvia dopo 10 secondi.
- Rifiuta gli snapshot da cui la Deck ripartirebbe senza accesso SSH o con un GRUB diverso.
- Prova reale sulla Deck: modifica di prova annullata, Deck tornata in 44 secondi, stato precedente
  recuperabile nello snapshot 18. 67 test.

## 0.1.11 — 2026-10-25

Ciclo 01, task O3.T2: componente `deck snapshot`, elenco e creazione.

- `deck snapshot` elenca gli snapshot come snapper e indica per ognuno se è avviabile dal menu di GRUB
  (`in_grub`, `null` mentre grub-btrfsd riscrive il menu).
- `deck snapshot create description="…"` crea uno snapshot singolo, marcato `source: deck`.
- Il rollback compare tra le azioni come non ancora disponibile.
- Verificato sulla Deck: elenco identico a snapper; lo snapshot creato da `deck` è comparso nel menu di
  GRUB dopo 7 secondi. 56 test.

## 0.1.10 — 2026-10-25

Ciclo 01, task O3.T5: sullo schermo della Deck anche la risposta di ogni comando (richiesta dell'utente).

- Sotto ogni comando compare il suo output, con gli errori in rosso; le righe lunghe vanno a capo su al
  massimo 3 righe; la risposta JSON di `deck` è sostituita dalla riga di esito.
- Lo script di registrazione fa passare stdout e stderr da `tee`: chi lancia il comando riceve esattamente
  gli stessi dati, codice di uscita compreso (verificato con dati binari a ogni installazione). Esclusi i
  trasferimenti di file e le sessioni con terminale.
- Rete di sicurezza estesa: le versioni precedenti dello script e della configurazione SSH tornano da sole
  dopo 3 minuti se le prove falliscono.

## 0.1.9 — 2026-10-25

Ciclo 01, task O3.T4: schermo della Deck come terminale dell'agente (richiesta dell'utente).

- Al posto del login su `tty1` lo schermo mostra in tempo reale ogni comando SSH dell'agente e l'esito di
  ogni chiamata a `deck`, con testo ripulito e segreti oscurati.
- Comandi registrati tramite `BASH_ENV` per l'utente `agent`: autenticazione SSH invariata, e un errore
  nello script di registrazione non blocca i comandi.
- Installazione con snapshot e rete di sicurezza SSH (ripristino automatico in 3 minuti se `ssh`, `scp` o
  `rsync` non funzionano dopo la modifica). 42 test; documentazione in `docs/schermo.md`.

## 0.1.8 — 2026-10-25

Ciclo 01, task O3.T1: componente `deck status`.

- Stato della macchina in una schermata: sistema, hardware, carico, batteria, temperature, memoria, disco,
  rete e Wi-Fi, porte in ascolto, servizi, snapshot, sincronizzazione dell'ora.
- Avvisi con codici stabili: oggi segnala Wi-Fi a 2,4 GHz, LLMNR superfluo sulla LAN e ventola non leggibile.
- Letture robuste in `agentdeck/system.py`: una lettura che fallisce non rompe la schermata.
- Controllo dal vivo: 23 valori su 23 coincidono con gli strumenti classici di Linux; 34 test verdi.
- Installato `iw` sulla Deck (snapshot 8 e 9) e aggiunto all'elenco pacchetti di `install/install.sh`.

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
