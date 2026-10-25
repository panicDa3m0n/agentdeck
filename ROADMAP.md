<!-- FILE GENERATO DALLA GOVERNANCE — non modificarlo a mano.
     Ogni modifica manuale viene rilevata e scartata al comando successivo.
     Si aggiorna SOLO con i comandi wf.sh (obj-add, task-add, task-start,
     task-close, note-add, req-add, ...). -->


# ROADMAP — linuxai-steamdeck  ·  ciclo 02: La Deck come server gestito dall'agente: rete, servizi, aggiornamenti, schermo

_Dossier di progetto: [PROGETTO.md](PROGETTO.md)_

## Stato corrente

- **Obiettivo attivo:** —
- **Task attiva:** —
- **Ultima task gestita:** —
- **Ultimo aggiornamento:** 2026-10-25 19:08

## Richieste attive

_Mancanze di progetto che l'agente non può risolvere da solo. L'utente le conferma in chat, poi vengono chiuse con `req-resolve`._

- `R1` (generale) Sbloccare la conferma del ciclo 02: debt-resolve è richiesto da setup --confermato ma negato dal controllo dei comandi nel passo 6 del setup

## Obiettivi

### `O4` Rete gestita dall'agente: deck network — in corso

**Gate obiettivo:** deck network mostra lo stato reale di rete, Wi-Fi e porte; gli avvisi di rete di deck status puntano ad azioni di deck network; LLMNR spento e banda Wi-Fi migliore disponibile applicati con anteprima e rete di sicurezza; ssh agentdeck funziona dopo ogni modifica (INV-1).

- [ ] `O4.T1` Componente network: interfacce, Wi-Fi, risoluzione dei nomi, porte (N8) — *perimetro:* `deck/, componente network, componente status`
  *gate previsto:* deck network riporta interfacce, Wi-Fi collegato e reti visibili con le loro bande, stato di mDNS e LLMNR, porte in ascolto; ogni valore coincide con ip, iw, resolvectl e ss; gli avvisi WIFI_BAND_2G e LLMNR_LISTENING di deck status puntano alle azioni di deck network.
- [ ] `O4.T2` Azioni di rete con anteprima e rete di sicurezza: LLMNR e banda Wi-Fi — *perimetro:* `deck/, configurazione di rete sulla Deck, install/install.sh`
  *gate previsto:* Con anteprima e conferma: LLMNR spento (porta 5355 non più in ascolto) e Wi-Fi sulla banda a 5 GHz se la rete di casa la offre, altrimenti azione non disponibile con il motivo; snapshot prima; ripristino automatico se dopo la modifica la Deck non è raggiungibile, provato; ssh agentdeck funziona; correzioni riportate in install/install.sh.

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

_nessuna annotazione._
