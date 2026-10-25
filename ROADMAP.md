<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 02: La Deck come server gestito dall'agente: rete, servizi, aggiornamenti, schermo

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** —
- **Task attiva:** —
- **Ultima task gestita:** `O4.T2` — completata — deck network: llmnr_off/on e prefer_5ghz con ritorno automatico, provati dal vivo; Deck sui 5 GHz anche dopo riavvio, ssh ok, 11/11, 100 test
- **Ultimo aggiornamento:** 2026-10-25 19:44

## Richieste attive

_nessuna richiesta in attesa._

## Obiettivi

### `O4` Rete gestita dall'agente: deck network — chiuso

**Gate obiettivo:** deck network mostra lo stato reale di rete, Wi-Fi e porte; gli avvisi di rete di deck status puntano ad azioni di deck network; LLMNR spento e banda Wi-Fi migliore disponibile applicati con anteprima e rete di sicurezza; ssh agentdeck funziona dopo ogni modifica (INV-1).
**Chiuso:** 2026-10-25 19:44 — approvato

- [x] `O4.T1` Componente network: interfacce, Wi-Fi, risoluzione dei nomi, porte (N8) — *perimetro:* `deck/, componente network, componente status, docs/deck.md, docs/hardware.md`
  *gate previsto:* deck network riporta interfacce, Wi-Fi collegato e reti visibili con le loro bande, stato di mDNS e LLMNR, porte in ascolto; ogni valore coincide con ip, iw, resolvectl e ss; gli avvisi WIFI_BAND_2G e LLMNR_LISTENING di deck status puntano alle azioni di deck network. · *gate confermato:* ✔ deck network: 11/11 valori uguali a ip, iw, resolvectl, ss; rete sorella a 5 GHz riconosciuta; avvisi di status puntano a /network; 80 test.
  *rischio:* 10/100 — Componente in sola lettura: legge interfacce, Wi-Fi (con una scansione delle reti visibili), risoluzione dei nomi e porte; non cambia configurazione. Le azioni di rete compaiono come non disponibili fino a O4.T2.
- [x] `O4.T2` Azioni di rete con anteprima e rete di sicurezza: LLMNR e banda Wi-Fi — *perimetro:* `deck/, configurazione di rete sulla Deck, install/install.sh`
  *gate previsto:* Con anteprima e conferma: LLMNR spento (porta 5355 non più in ascolto) e Wi-Fi sulla banda a 5 GHz se la rete di casa la offre, altrimenti azione non disponibile con il motivo; snapshot prima; ripristino automatico se dopo la modifica la Deck non è raggiungibile, provato; ssh agentdeck funziona; correzioni riportate in install/install.sh. · *gate confermato:* ✔ deck network: llmnr_off/on e prefer_5ghz con ritorno automatico, provati dal vivo; Deck sui 5 GHz anche dopo riavvio, ssh ok, 11/11, 100 test
  *rischio:* 45/100 — Cambia la rete della Deck, che è il canale dell'agente (INV-1): LLMNR è a basso rischio, il passaggio a un'altra rete Wi-Fi può far perdere il collegamento o cambiare IP. Mitigazioni: snapshot prima, verifica dopo ogni modifica, e per il Wi-Fi un ritorno automatico ai 2,4 GHz se entro pochi minuti l'agente non conferma di raggiungere la Deck.
  *annotazioni:* `N11`, `N12`, `N13`, `N14`

### `O5` Servizi e log gestiti dall'agente: deck service, deck logs — in corso

**Gate obiettivo:** deck service mostra e governa i servizi di systemd con anteprima per le azioni che interrompono qualcosa e rifiuto per quelli da cui dipende l'accesso (INV-1); deck logs restituisce il journal strutturato con il testo dei log solo nei dati (INV-4).

- [ ] `O5.T1` Componente service: elenco, stato e azioni sui servizi — *perimetro:* `deck/, componente service`
  *gate previsto:* deck service elenca i servizi come systemctl, con stato, abilitazione e servizi falliti; start, stop, restart, enable e disable funzionano su un servizio di prova, quelli che interrompono qualcosa con anteprima; stop e disable di sshd, systemd-networkd, iwd e systemd-resolved rifiutati con il motivo (INV-1).
- [ ] `O5.T2` Componente logs: journal strutturato per servizio, periodo e gravità — *perimetro:* `deck/, componente logs, componente service`
  *gate previsto:* deck logs restituisce le righe del journal filtrate per servizio, periodo e gravità, uguali a journalctl -o json; il testo dei log sta solo nei dati e un test con una riga di log malevola verifica che non entri nel canale istruzioni (INV-4); da deck service si arriva ai log del servizio.

### `O6` Aggiornamenti sicuri: deck update — in corso

**Gate obiettivo:** Un aggiornamento reale del sistema fatto da deck update: anteprima dei pacchetti, snapshot prima e dopo, verifica automatica dopo l'applicazione, rollback indicato se la verifica fallisce; la Deck resta raggiungibile, anche dopo il riavvio se l'aggiornamento lo richiede.

- [ ] `O6.T1` Componente update: anteprima, applicazione e verifica degli aggiornamenti — *perimetro:* `deck/, componente update, pacchetti sulla Deck, install/install.sh`
  *gate previsto:* deck update elenca gli aggiornamenti disponibili con versione attuale e nuova e segnala kernel e GRUB (riavvio, coerenza di GRUB); l'applicazione con conferma crea gli snapshot, aggiorna, verifica servizi e accesso e indica il rollback se qualcosa non va; provato con un aggiornamento reale sulla Deck, riavvio compreso se richiesto.

### `O7` Schermo leggibile e compatto, sistema pulito: deck screen — in corso

**Gate obiettivo:** L'agente legge con deck screen cosa mostra lo schermo e ne sceglie la modalità; la modalità compatta riduce la verbosità; i vecchi sistemi lasciati dai rollback si eliminano con anteprima da deck snapshot.

- [ ] `O7.T1` Componente screen: lettura dello schermo e modalità compatta (N9, N10) — *perimetro:* `deck/, deck/screen/, docs/schermo.md`
  *gate previsto:* deck screen restituisce nei dati le righe visibili sullo schermo, uguali a /dev/vcsu1, e lo stato del servizio; l'azione mode passa tra completa e compatta (per ogni comando poche righe di risposta e il numero di righe nascoste), verificato leggendo lo schermo; il testo dello schermo sta solo nei dati (INV-4).
- [ ] `O7.T2` Pulizia dei vecchi sistemi lasciati dai rollback — *perimetro:* `deck/, componente snapshot, subvolumi Btrfs sulla Deck`
  *gate previsto:* deck snapshot mostra i vecchi sistemi @old-* con lo spazio occupato e li elimina con anteprima e conferma, subvolumi annidati compresi; provato su @old-20261025-180914; il sistema in uso e gli snapshot restano intatti.

## Annotazioni

_Una riga per nota, sempre legata a una task. `wf.sh notes` per leggerle._

- `N11` (`O4.T2`) Scoperto in O4.T1 (25/10): il router non trasmette la rete di casa su due bande con lo stesso nome; i 5 GHz sono una rete distinta, WINDTRE - 2065D6 - 5Ghz (BSSID 58:4b:bc:20:65:d7, segnale -20 dBm, canale 5500 MHz). prefer_5ghz quindi significa collegarsi a un'altra rete: serve la sua password (richiesta R2); tenere il profilo a 2,4 GHz come riserva e tornarci da soli se dopo il cambio la Deck non è raggiungibile. — 2026-10-25 19:15
- `N12` (`O4.T2`) Avanzamento O4.T2 (25/10, 19:31): llmnr_off provato dal vivo (snapshot 20 e 21, porta 5355 chiusa, DNS e mDNS ok, llmnr_on riapre la porta). prefer_5ghz: primo tentativo fallito subito, iwd non vedeva la rete (P12, corretto con scansione di iwd); secondo tentativo sui 5 GHz in 12 s, stesso IP .49, SSH ok, stessa password; senza conferma il ritorno è scattato a 180 s. Manca la prova con keep_5ghz. — 2026-10-25 19:31
- `N13` (`O4.T2`) Valutazione d'impatto O4.T2: INV-1 retto (profilo 2,4 GHz tenuto come riserva, ritorno automatico provato, riavvio Deck ok in 30 s, IP .49 invariato). Un rollback a uno snapshot precedente al 19:32 riporta la Deck sui 2,4 GHz, ancora raggiungibile. Una reinstallazione spegne LLMNR e preferisce i 5 GHz, ma il profilo 5 GHz va ricreato con prefer_5ghz. La password resta sulla Deck in file root 600, mai stampata (INV-6). Nessun effetto su snapshot, schermo, ssh. — 2026-10-25 19:35
- `N14` (`O4.T2`) Per una roadmap futura, approvato dall'utente il 25/10: componente deck secrets per i segreti che vengono da fuori (prima la chiave API dell'agente interno). L'agente chiede il segreto con nome e scopo; l'umano lo consegna da un canale laterale, mai dalla chat: file in secrets/ inviato via pipe con ssh, pagina usa e getta sulla LAN aperta da un QR sullo schermo della Deck, più avanti un gestore di password con token revocabile. Conservato cifrato sulla Deck (systemd-creds, TPM se attivo); l'agente vede solo nomi e metadati, mai il valore; il valore va diretto a chi lo usa (LoadCredential), ogni uso registrato. — 2026-10-25 19:44
