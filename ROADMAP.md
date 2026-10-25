<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 01: Prima interfaccia agentica: protocollo, stato e snapshot

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** `O3` Primi componenti usati dall'agente: stato del sistema e snapshot — 5 task: 2 completate, 1 in corso, 2 da fare, 0 bloccate
- **Task attiva:** `O3.T5` Schermo della Deck: anche la risposta di ogni comando — in corso · rischio 35/100
- **Ultima task gestita:** `O3.T4` — completata — Schermo Deck: comandi agente ed esiti deck in tempo reale (verificato da /dev/vcsu1); snapshot 10; ssh, scp, rsync ok; docs/schermo.md.
- **Fase:** `in_progress`
- **Ultimo aggiornamento:** 2026-10-25 17:57

## Richieste attive

_nessuna richiesta in attesa._

## Obiettivi

### `O1` Base operativa affidabile per l'agente — chiuso

**Gate obiettivo:** Repository con identità git personale e remote privato su GitHub con le versioni pubblicate; documentazione di base indicizzata e collegata al codice; dopo due riavvii consecutivi la Deck mantiene lo stesso IP, risponde subito a ssh agentdeck e il comando hostname funziona.
**Chiuso:** 2026-10-25 16:54 — approvato

- [x] `O1.T1` Identità git personale e remote privato su GitHub — *perimetro:* `repository git locale, remote GitHub`
  *gate previsto:* git log mostra come autore l'identità personale di Davide su tutti i commit, impostata solo per questo repository; esiste un repository GitHub privato sotto l'account personale panicDa3m0n con main pubblicato e il tag della versione corrente; nessuna credenziale sul remote (INV-6). · *gate confermato:* ✔ Autore personale su tutti i commit; repo privato panicDa3m0n/agentdeck con main e tag v0.1.0, verificato via API; nessuna credenziale online.
  *rischio:* 15/100 — Riscrive l'autore di un solo commit mai pubblicato e crea un repository privato su GitHub: tutto reversibile (si può riscrivere di nuovo o eliminare il repository); unico punto delicato è non pubblicare credenziali, controllato prima del push.
  *annotazioni:* `N1`
- [x] `O1.T2` IP stabile della Deck sulla rete di casa — *perimetro:* `configurazione rete sulla Deck, install/install.sh`
  *gate previsto:* Snapshot creato prima della modifica; dopo due riavvii consecutivi l'IPv4 di wlan0 resta lo stesso e ssh agentdeck funziona al primo tentativo; la correzione è riportata anche in install/install.sh. · *gate confermato:* ✔ SendRelease=no sulla Deck e in install.sh; snapshot 4 prima; dopo 2 riavvii consecutivi IP sempre .49; ssh agentdeck riuscito 5 volte su 5 al primo tentativo.
  *rischio:* 25/100 — Tocca la configurazione di rete della Deck, che è l'unico canale dell'agente (INV-1): la modifica è minima (non rilasciare il lease DHCP allo spegnimento), una chiave sconosciuta verrebbe solo ignorata; snapshot prima della modifica e due riavvii di prova. Se la rete non tornasse servirebbe la chiavetta di recupero.
- [x] `O1.T3` Comandi di base attesi dagli agenti — *perimetro:* `pacchetti sulla Deck, install/install.sh`
  *gate previsto:* hostname restituisce agentdeck; il pacchetto è installato con pacman e snapper mostra gli snapshot pre e post dell'installazione; il pacchetto è aggiunto all'elenco di install/install.sh. · *gate confermato:* ✔ inetutils installato con pacman (snapshot pre 5 e post 6 da snap-pac); hostname restituisce agentdeck; pacchetto aggiunto a install/install.sh.
  *rischio:* 10/100 — Installa un piccolo pacchetto ufficiale (inetutils, che fornisce hostname) con pacman: snap-pac crea da solo gli snapshot prima e dopo (INV-3) e non tocca rete, SSH o avvio.
- [x] `O1.T4` Documentazione di base del progetto, indicizzata e collegata al codice — *perimetro:* `README.md, docs/, intestazioni degli script in live/ e install/, PRINCIPI.md, live/*.sh, install/*.sh`
  *gate previsto:* README.md con panoramica e link; docs/README.md come indice; documenti per principi, chiavetta live, installazione e accesso alla Deck; ogni script in live/ e install/ rimanda al suo documento e ogni documento rimanda agli script; tutto pubblicato sul remote. · *gate confermato:* ✔ README, indice docs/ e 5 documenti; PRINCIPI con INV-10; 57 link verificati senza rotture; script e documenti collegati a vicenda; tutto su origin/main.
  *rischio:* 5/100 — Solo documentazione e commenti di intestazione negli script: nessuna modifica al comportamento del codice né alla Deck.
  *annotazioni:* `N2`, `N3`, `N4`
- [x] `O1.T5` Accesso SSH affidabile dal Mac — *perimetro:* `~/.ssh/config (voci agentdeck), docs/accesso.md`
  *gate previsto:* La voce agentdeck in ~/.ssh/config punta all'IP stabile 192.168.1.49 e il nome .local resta come alias agentdeck-mdns; 10 tentativi consecutivi di ssh agentdeck riusciti al primo colpo; backup della configurazione precedente; docs/accesso.md aggiornato. · *gate confermato:* ✔ ssh agentdeck usa l'IP stabile .49 (HostKeyAlias), alias agentdeck-mdns sul nome; backup fatto; 10 collegamenti su 10 al primo colpo; accesso.md aggiornato.
  *rischio:* 10/100 — Modifica solo la voce agentdeck nella configurazione SSH del Mac, con backup prima: se qualcosa non va si ripristina il file; la Deck e il suo accesso non cambiano.

### `O2` Protocollo dell'interfaccia agentica: schermate interattive e autoprompting — chiuso

**Gate obiettivo:** Protocollo scritto e approvato dall'utente; il comando deck installato sulla Deck risponde con schermate JSON conformi al protocollo, con le istruzioni separate dai dati (INV-4).
**Chiuso:** 2026-10-25 17:37 — approvato

- [x] `O2.T1` Specifica del protocollo di schermata e autoprompting — *perimetro:* `docs/`
  *gate previsto:* docs/protocollo.md descrive la struttura della schermata (dati, azioni, navigazione, avvisi, errori, conferme con anteprima, istruzioni), le regole di autoprompting e di sicurezza del canale istruzioni, con esempi reali; linguaggio di implementazione deciso; approvato esplicitamente dall'utente. · *gate confermato:* ✔ docs/protocollo.md approvato: schermate, azioni, conferme, errori, autoprompting, INV-4, 8 esempi reali; Python 3, testi in inglese.
  *rischio:* 10/100 — Produce solo un documento di specifica in docs/ da approvare con l'utente: nessun codice e nessuna modifica alla Deck; il rischio è progettuale (un protocollo sbagliato peserebbe su tutti i componenti), per questo il gate richiede l'approvazione esplicita.
- [x] `O2.T2` Motore deck e installazione sulla Deck — *perimetro:* `deck/, script di installazione del comando, docs/deck.md, docs/README.md, PRINCIPI.md, README.md, docs/protocollo.md`
  *gate previsto:* Sulla Deck: deck senza argomenti restituisce la schermata principale con l'elenco dei componenti; un indirizzo inesistente restituisce una schermata di errore strutturata con azioni per uscirne; ogni risposta è JSON valido conforme al protocollo; l'installazione è ripetibile da uno script nel repository. · *gate confermato:* ✔ deck sulla Deck: home con componenti, errori strutturati, 8 chiamate reali conformi, 22 test verdi, ~0,09 s; install.sh ripetuto con successo.
  *rischio:* 20/100 — Installa il pacchetto python sulla Deck (snap-pac fa snapshot prima e dopo) e aggiunge codice nostro in /opt/agentdeck con il comando /usr/local/bin/deck: tutto reversibile, non tocca rete, SSH o avvio; il rischio è nella correttezza del motore, coperta da test di conformità e di iniezione.
  *annotazioni:* `N6`

### `O3` Primi componenti usati dall'agente: stato del sistema e snapshot — in corso

**Gate obiettivo:** L'agente usa deck status e deck snapshot al posto dei comandi manuali; un rollback reale riporta il sistema allo stato salvato e ssh agentdeck funziona dopo il riavvio.

- [x] `O3.T1` Componente status: monitor attività e informazioni di sistema — *perimetro:* `deck/, componente status, docs/deck.md, install/install.sh`
  *gate previsto:* deck status riporta hardware, temperature, batteria, memoria, disco, rete, servizi falliti e snapshot; ogni valore coincide con quello letto dai comandi di sistema; le anomalie note (per esempio Wi-Fi a 2,4 GHz) compaiono come avvisi con azioni suggerite. · *gate confermato:* ✔ deck status sulla Deck: 23/23 valori coincidono con gli strumenti classici, avvisi WIFI_BAND_2G, LLMNR, ventola; 34 test verdi; 0,27 s.
  *rischio:* 15/100 — Componente in sola lettura: legge /proc, /sys e comandi di stato (alcuni con sudo); l'unica modifica di sistema prevista è installare il piccolo pacchetto ufficiale iw per leggere il Wi-Fi in modo affidabile, con gli snapshot di snap-pac.
  *annotazioni:* `N5`, `N8`
- [ ] `O3.T2` Componente snapshot: elenco e creazione — *perimetro:* `deck/, componente snapshot`
  *gate previsto:* deck snapshot elenca gli stessi snapshot di snapper; la creazione da deck produce uno snapshot visibile in snapper e nel menu snapshot di GRUB.
- [ ] `O3.T3` Rollback con anteprima e conferma — *perimetro:* `deck/, componente snapshot, subvolumi Btrfs sulla Deck`
  *gate previsto:* Prova reale: dopo snapshot e modifica di prova, il rollback mostra l'anteprima delle conseguenze, si conferma con il codice, la Deck riavvia nello stato salvato, la modifica di prova è sparita e ssh agentdeck funziona; lo stato precedente resta recuperabile come snapshot.
- [x] `O3.T4` Schermo della Deck: attività dell'agente visibile come un terminale — *perimetro:* `configurazione SSH e servizi sulla Deck, deck/, docs/, README.md`
  *gate previsto:* Al posto del login, sullo schermo della Deck un terminale mostra in tempo reale ogni comando eseguito dall'agente via SSH e l'esito delle chiamate a deck; verificato leggendo il contenuto della console; snapshot prima; ssh agentdeck, scp e rsync funzionano ancora (INV-1); documentato. · *gate confermato:* ✔ Schermo Deck: comandi agente ed esiti deck in tempo reale (verificato da /dev/vcsu1); snapshot 10; ssh, scp, rsync ok; docs/schermo.md.
  *rischio:* 35/100 — Tocca la configurazione SSH (solo SetEnv per l'utente agent, nessun cambio di autenticazione) e sostituisce il login su tty1 con un servizio: l'accesso SSH è l'unico canale (INV-1), quindi snapshot prima, sshd -t, e una rete di sicurezza che annulla da sola la modifica SSH dopo 3 minuti se non confermata dopo i test di ssh, scp e rsync.
  *annotazioni:* `N7`, `N9`
- [~] `O3.T5` Schermo della Deck: anche la risposta di ogni comando — *perimetro:* `deck/screen/, deck/install.sh, deck/tests/, docs/schermo.md, README.md, docs/README.md`
  *gate previsto:* Sotto ogni comando lo schermo mostra il suo output (normale e, in rosso, gli errori), le risposte di deck riassunte, i trasferimenti di file esclusi; per chi esegue il comando stdout, stderr, codice di uscita e dati binari restano identici (verificato); ssh, scp e rsync funzionano; rete di sicurezza anche per lo script di registrazione; documentato.
  *rischio:* 35/100 — Lo script di registrazione passerà da tee l'output di ogni comando SSH dell'agente: tocca il percorso di input/output di tutti i comandi, quindi INV-1. Mitigazioni: trasferimenti e terminali interattivi esclusi, errori dello script non bloccanti, snapshot e ripristino automatico in 3 minuti se le prove falliscono.

## Annotazioni

_Una riga per nota, sempre legata a una task. `wf.sh notes` per leggerle._

- `N1` (`O1.T1`) Richiesta dell'utente alla conferma della roadmap (25/10): appena chiuso il setup registrare due invarianti, non registrabili durante il passo 6. INV-8: ogni versione si pubblica sul remote privato appena chiusa (commit e tag su GitHub, account panicDa3m0n). INV-9: documentazione sempre completa, organizzata per argomento in più file in docs/ con indice e collegata dal codice stesso, e viceversa; una modifica non è conclusa finché la documentazione non la riflette. Rieseguire anche: versione --scegli governance --dove VERSION --pubblica. — 2026-10-25 16:01
- `N2` (`O1.T4`) Aggiungere a PRINCIPI.md (o al documento dei principi in docs/) il principio approvato dall'utente il 25/10, registrato come INV-10: si interviene al livello più alto che risolve il problema (configurazione, strato agentico, sostituzione di componenti); il codice di base si modifica solo per un bisogno reale e con decisione esplicita. Includere la tabella dei quattro livelli e il paragone con macOS e Android. — 2026-10-25 16:05
- `N3` (`O1.T4`) Documentare in docs/ il setup git e GitHub: identità personale impostata solo nel repository (Davide, davideditrani94@gmail.com), remote privato https://github.com/panicDa3m0n/agentdeck, credential helper locale che usa gh auth token --user panicDa3m0n (indipendente dall'account gh attivo), tag v<versione> a ogni versione chiusa (INV-8). — 2026-10-25 16:07
- `N4` (`O1.T4`) Documentare nell'accesso alla Deck: IP stabile 192.168.1.49 grazie a SendRelease=no (O1.T2, testato con due riavvii); ssh agentdeck usa il nome agentdeck.local; se il nome non si risolve (trappola P2) usare ssh -o HostName=192.168.1.49 agentdeck. Una prenotazione DHCP sul router renderebbe l'IP fisso anche dopo spegnimenti lunghi: richiede l'accesso dell'utente al router. — 2026-10-25 16:12
- `N5` (`O3.T1`) Dalla verifica INV-5 al gate di O1 (25/10): sulla Deck sono in ascolto 22 (SSH), 5355 (LLMNR di systemd-resolved, su tutta la LAN) e 53 solo su localhost. LLMNR non serve perché usiamo mDNS: deck status dovrebbe mostrare le porte in ascolto e segnalare LLMNR come superfluo, con l'azione suggerita LLMNR=no in resolved.conf. — 2026-10-25 16:18
- `N6` (`O2.T2`) Dall'approvazione di O2.T1 (25/10): implementare deck seguendo docs/protocollo.md, approvato; Python 3 solo libreria standard; testi per l'agente in inglese. Da fare: installare il pacchetto python sulla Deck con snapshot (INV-3); ogni modulo rimanda a docs/protocollo.md (INV-9); test di conformità di ogni schermata e test di iniezione nel canale istruzioni (INV-4); aggiungere a PRINCIPI.md le righe di decisione: protocollo deck v1, Python 3, testi agente in inglese. — 2026-10-25 17:20
- `N7` (`O3.T4`) Richiesta dell'utente del 25/10: sullo schermo della Deck vede solo agentdeck login; vuole vedere, come in un terminale, cosa sta facendo l'agente in base ai comandi. Da lavorare subito dopo O3.T1. Idea da discutere nel brief: wrapper dei comandi SSH dell'agente che registra ogni comando nel journal, servizio su tty1 al posto di getty che lo mostra; verifica leggendo /dev/vcs1. Attenzione: un comando con segreti sulla riga di comando comparirebbe a schermo e nel journal. — 2026-10-25 17:40
- `N8` (`O3.T1`) Bisogno emerso usando deck status (25/10): gli avvisi WIFI_BAND_2G e LLMNR_LISTENING hanno action null perché manca un componente di rete su cui agire. Candidato per il prossimo ciclo: componente /network (banda Wi-Fi preferita, LLMNR=no, porte in ascolto) collegato dagli avvisi di status. — 2026-10-25 17:43
- `N9` (`O3.T4`) Idea emersa verificando lo schermo (25/10): poter leggere lo schermo è utile all'agente (INV-2: tutto osservabile). Candidato per un ciclo futuro: componente deck /screen che restituisce in data le righe visibili su tty1 (da /dev/vcsu1) e lo stato del servizio agentdeck-screen. — 2026-10-25 17:48
