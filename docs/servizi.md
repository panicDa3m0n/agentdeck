# Servizi ospitati

L'area in cui la Deck ospita i servizi: progetti (da GitHub o scritti da noi) che girano ciascuno per conto suo,
si avviano, si fermano e si abilitano all'avvio uno per uno.

Codice: [`servizi/install-servizi.sh`](../servizi/install-servizi.sh),
[`servizi/nuovo-servizio.sh`](../servizi/nuovo-servizio.sh),
[`servizi/agentdeck-servizio@.service`](../servizi/agentdeck-servizio@.service).
Indice: [README.md](README.md).

L'area l'ha preparata e verificata sulla Deck l'agente, nella sessione reale del 26/10/2026 (O10.T4). L'ha
lasciata come consegna in `~/agentdeck/consegna`, e una sessione dal Mac l'ha portata nel repository (O10.T12):
l'unità e il comando sono identici a quelli installati, verificati con i checksum.

## Struttura

```
/srv/servizi/                 subvolume Btrfs @servizi, montato da fstab (nofail)
└── <nome>/                   agent:srv-<nome> 0750
    ├── LEGGIMI.md            cosa fa, repository e commit, porta, come si aggiorna
    ├── avvia                 comando di avvio in primo piano (eseguibile = pronto)
    ├── app/                  codice: lo scrive l'agente, il servizio lo legge soltanto
    ├── config/env            variabili d'ambiente e segreti (mai in git, INV-6)
    └── dati/                 dati persistenti: l'unica cartella scrivibile dal servizio
```

Ogni servizio è un'istanza dell'unità modello `agentdeck-servizio@<nome>.service` e gira come utente di sistema
`srv-<nome>`, senza shell né login.

**Perché un subvolume a parte.** Lo snapshot di sistema (snapper, configurazione `root`) copre solo `@`. I dati dei
servizi stanno in `@servizi`: un rollback del sistema non li riporta indietro e non li cancella. Il rovescio della
medaglia: gli snapshot di sistema non proteggono i dati dei servizi (vedi "Da fare"). La riga di fstab sta in `@`, quindi
un rollback a uno snapshot precedente all'installazione la toglie: i dati restano nel subvolume e basta rieseguire
`install-servizi.sh`.

## Isolamento

L'unità modello, per ogni servizio:

- filesystem di sistema in sola lettura (`ProtectSystem=strict`), scrittura solo in `dati/`;
- niente home (`ProtectHome`), `/tmp` privato, niente dispositivi, nessuna capability, nessun nuovo privilegio;
- non vede gli altri servizi: ogni cartella è leggibile solo dal suo gruppo `srv-<nome>`;
- limiti di risorse (`MemoryMax=3G`, `TasksMax=512`, `CPUWeight=80`, `OOMScoreAdjust=500`): un servizio non toglie
  memoria o CPU all'accesso dell'agente (INV-1);
- riavvio automatico se cade (`Restart=on-failure`), al massimo 5 volte in 5 minuti.

`systemd-analyze security` dà 3.0 ("OK"). Impostazioni diverse per un singolo servizio (più memoria, dipendenze da
un altro servizio) vanno in un drop-in: `/etc/systemd/system/agentdeck-servizio@<nome>.service.d/*.conf`.

## Rete

L'unità imposta `HOST=127.0.0.1`: per convenzione un servizio ascolta solo sulla Deck. Esporlo sulla rete di casa
(`HOST=0.0.0.0` in `config/env`) è una decisione esplicita dell'utente, ed esporlo su internet anche (INV-5). Oggi
sulla Deck non c'è un firewall: la convenzione non è imposta dal sistema (vedi "Da fare"). La porta di ogni servizio
sta in `config/env` (`PORT=`) e nel suo `LEGGIMI.md`.

## Uso

Installare l'area (una volta, ripetibile), dopo uno snapshot:

```
deck snapshot create description="area servizi"
sudo bash servizi/install-servizi.sh
```

Dal Mac, dalla radice del repository, è un passo a sé, come `install/remote-access.sh`: `deck/install.sh` non lo
chiama, perché tocca fstab e i subvolumi.

```
ssh agentdeck 'deck snapshot create "description=area servizi"'
scp -r -q servizi agentdeck:/tmp/agentdeck-servizi && ssh agentdeck 'sudo bash /tmp/agentdeck-servizi/install-servizi.sh'
```

Aggiungere un servizio:

```
sudo agentdeck-nuovo-servizio <nome>          # cartelle e utente srv-<nome>; non avvia nulla
git clone <repo> /srv/servizi/<nome>/app      # o copia del codice
$EDITOR /srv/servizi/<nome>/avvia             # comando in primo piano, poi chmod 0750
$EDITOR /srv/servizi/<nome>/config/env        # PORT= e le variabili del progetto
```

Gestirlo con `deck service`, con le stesse anteprime e conferme degli altri servizi:

```
deck service start   name=agentdeck-servizio@<nome>
deck service stop    name=agentdeck-servizio@<nome>    # anteprima e conferma
deck service enable  name=agentdeck-servizio@<nome>    # parte a ogni avvio (snapshot prima)
deck service disable name=agentdeck-servizio@<nome>
deck logs query unit=agentdeck-servizio@<nome> since=10m
```

Le dipendenze di un progetto (virtualenv Python, `node_modules`, binari compilati) stanno dentro `app/`, preparate
dall'agente prima dell'avvio; il servizio non può installare nulla mentre gira. Runtime di sistema mancanti
(Node, ...) si installano con pacman, con snapshot.

Togliere un servizio: fermarlo e disabilitarlo con deck, poi `sudo rm -rf /srv/servizi/<nome>` e
`sudo userdel srv-<nome>`.

## Verifica (2026-10-26)

Servizio di prova `prova` (server HTTP Python su 127.0.0.1:8099), avviato e fermato con `deck service`:
risposta 200 su 127.0.0.1, nessuna risposta dall'IP di rete; processo come `srv-prova`; scrittura in `dati/`
permessa, in `app/` e in `/etc` negata, lettura di `/home/agent/.ssh` negata. Poi rimosso. `install-servizi.sh`
rieseguito senza cambiamenti; `findmnt --verify` senza errori.

## Da fare

- **`deck servizi`**: un componente che elenca le cartelle di `/srv/servizi` con lo stato dell'unità. `deck service`
  mostra un'istanza solo mentre è caricata: un servizio fermo non compare. Poi le azioni su un servizio intero:
  crea, aggiorna da git (snapshot dei dati prima), rimuovi (anteprima).
- **Snapshot dei dati**: una configurazione snapper `servizi` per `@servizi`, da usare prima di aggiornare o
  rimuovere un servizio (INV-3).
- **Firewall** (nftables): permettere da LAN solo SSH e le porte dei servizi esposti per decisione. Tocca la rete:
  va fatto con una rete di sicurezza che si annulla da sola (INV-1).
