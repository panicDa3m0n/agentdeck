# Accesso alla Deck

Come l'agente raggiunge e gestisce la Deck, con quali protezioni, e cosa fare se non risponde.
Indice: [README.md](README.md).

## Collegarsi

Dal Mac basta, in casa o fuori:

```bash
ssh agentdeck
```

Le voci in `~/.ssh/config` del Mac:

```
Match originalhost agentdeck exec "ping -c 1 -t 1 -q 192.168.1.49 >/dev/null 2>&1"
  HostName 192.168.1.49
  Port 22

Host agentdeck
  HostName scarlethome.ddns.net
  Port 49222
  HostKeyAlias agentdeck
  User agent
  IdentityFile ~/.ssh/id_ed25519_steamdeck
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new

Host agentdeck-lan
  HostName 192.168.1.49
  HostKeyAlias agentdeck
  User agent
  IdentityFile ~/.ssh/id_ed25519_steamdeck
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new

Host agentdeck-wan
  HostName scarlethome.ddns.net
  Port 49222
  HostKeyAlias agentdeck
  User agent
  IdentityFile ~/.ssh/id_ed25519_steamdeck
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new

Host agentdeck-mdns
  HostName agentdeck.local
  HostKeyAlias agentdeck
  User agent
  IdentityFile ~/.ssh/id_ed25519_steamdeck
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
```

- `agentdeck` **sceglie da solo la strada**:
  - se la Deck risponde al ping su `192.168.1.49`, cioè se il Mac è nella rete di casa, usa l'**IP stabile** in
    LAN sulla porta 22;
  - altrimenti passa da internet, su `scarlethome.ddns.net` porta 49222 (vedi "Da fuori casa").

  Il controllo usa il ping e non una prova sulla porta 22, perché un collegamento a sshd chiuso senza login
  conta come penalità per le `PerSourcePenalties` di OpenSSH.
- `agentdeck-lan` è la **riserva solo LAN**, senza scelta automatica. `agentdeck-wan` passa sempre da internet:
  serve per le prove, e nel caso raro di un'altra rete in cui qualcosa risponde su `192.168.1.49`. In quel
  caso `ssh agentdeck` si ferma con l'avviso di chiave host cambiata, cioè fallisce senza rischi.
- `agentdeck-mdns` usa il nome `.local`: è una riserva se l'IP cambiasse, ma dal Mac non sempre si risolve
  (vedi sotto).
- `HostKeyAlias agentdeck`: l'identità della Deck (chiave host) si controlla sotto un solo nome, qualunque
  sia l'indirizzo usato, quindi un cambio di IP non provoca falsi allarmi.

- **Chiave:** `~/.ssh/id_ed25519_steamdeck`, senza passphrase così l'agente non resta bloccato. La parte
  privata resta solo sul Mac; quella pubblica è in [../live/authorized_keys](../live/authorized_keys).
- **Utente `agent`:** sudo senza password (agent-first: nessuna richiesta di password, INV-2).

## Indirizzo

- **Nome:** `agentdeck.local`, annunciato via mDNS da `systemd-resolved`.
- **IP stabile: `192.168.1.49`.** La Deck non restituisce l'indirizzo allo spegnimento (`SendRelease=no`,
  vedi [installazione.md](installazione.md)), quindi il router glielo riassegna. Verificato con due
  riavvii consecutivi.
- **Perché `ssh agentdeck` usa l'IP e non il nome:** sul Mac la query `.local` a volte riceve prima una
  risposta negativa dal DNS del router e solo dopo quella mDNS giusta, e `ssh` si ferma alla prima
  ("Could not resolve hostname agentdeck.local"). Con l'IP stabile il problema non si pone.
- **Se l'IP cambiasse** (per esempio dopo uno spegnimento più lungo della durata del lease): provare
  `ssh agentdeck-mdns`, oppure trovare il nuovo IP con `dns-sd -G v4 agentdeck.local`, poi aggiornare
  `HostName` nella voce `agentdeck`.
- **IP fisso anche dopo spegnimenti lunghi:** servirebbe una prenotazione DHCP sul router, che richiede il
  tuo accesso al router.

## Da fuori casa (O10.T5)

**Decisione dell'utente del 26/10/2026 (INV-5):** l'SSH della Deck è raggiungibile da internet, solo con la
chiave. È l'unico servizio esposto.

| Pezzo | Dove | Valore |
|---|---|---|
| Nome della linea di casa | DDNS del router | `scarlethome.ddns.net`, segue l'IP pubblico dinamico (verificato: 151.81.1.126 il 26/10) |
| Port forwarding | router ZTE F6746G, regola `agentdeck-ssh` | TCP, porta esterna **49222** → `192.168.1.49` porta 22 |
| Prenotazione DHCP | router | `192.168.1.49` per il MAC `14:d4:24:0a:8e:45` (Wi-Fi della Deck) |
| sshd | Deck, invariato | solo chiave, solo `agent`, niente root né password |
| sshguard | Deck, `/etc/sshguard.conf` e `/etc/sshguard/whitelist` | blocca nel firewall chi sbaglia; la rete di casa non è mai bloccata |

La regola di port forwarding e la prenotazione DHCP stanno sul router e le crea l'utente dal suo pannello
(`http://192.168.1.1`, nella sezione del port forwarding). La Deck non può aprirle da sola: il router annuncia
UPnP, ma rifiuta ogni azione con l'errore 800 "do not execute action(all)". UPnP resta spento: acceso,
permetterebbe a qualunque dispositivo di casa di aprire porte.

**sshguard** ([../install/sshguard.conf](../install/sshguard.conf),
[../install/sshguard-whitelist](../install/sshguard-whitelist), installato da
[../install/remote-access.sh](../install/remote-access.sh)):
- legge i login falliti dal journal, dove OpenSSH 10 li scrive come `sshd-session`;
- blocca con tabelle nftables proprie, `ip sshguard` e `ip6 sshguard`, che non toccano altre regole;
- funziona a punti: ogni tentativo sbagliato vale da 2 a 10. A 30 punti in 30 minuti l'indirizzo è bloccato
  per 2 minuti, e il blocco raddoppia a ogni recidiva. A 120 punti finisce nella lista nera
  (`/var/db/sshguard/blacklist.db`), che resta anche dopo un riavvio;
- non blocca mai `127.0.0.0/8`, `::1` e `192.168.1.0/24` (INV-1).

Si aggiunge alle `PerSourcePenalties` di OpenSSH 10, che già rallentano per qualche secondo chi sbaglia.

```bash
ssh agentdeck 'sudo nft list set ip sshguard attackers'           # indirizzi bloccati adesso
ssh agentdeck 'journalctl -u sshguard -b --no-pager -n 20 -o cat'  # cosa ha visto e bloccato
ssh agentdeck 'sudo nft delete element ip sshguard attackers "{ <ip> }"'  # sblocco a mano
```

Un indirizzo finito nella lista nera si toglie fermando sshguard e cancellando la sua riga da
`/var/db/sshguard/blacklist.db`.

**Rischi accettati con la decisione:**
- la porta 49222 è visibile a tutta internet e i bot proveranno a entrare: senza la chiave non entrano, e
  sshguard li blocca;
- resta il rischio di una futura falla in OpenSSH stesso, com'è successo nel 2024 con "regreSSHion". Lo riduce
  tenere Arch aggiornato (`deck update`, [deck.md](deck.md)).

**Tailscale, provato e scartato.** Si era scelta una rete privata con Tailscale: la Deck ci era entrata, ma sul
Mac l'estensione di rete di macOS è rimasta bloccata in "Connecting". L'app aveva chiesto il collegamento
all'estensione prima che venisse approvata, e né riaprire l'app né chiudere l'estensione l'hanno sbloccata.
Sulla Deck il pacchetto `tailscale` resta installato, ma `tailscaled` è fermo e disabilitato: niente porta
41641 e niente regole nel firewall. Per riprovarlo: `sudo systemctl enable --now tailscaled`.

## Sicurezza

- SSH solo con chiave; password e accesso di root via SSH disattivati; unico utente ammesso `agent`
  (`/etc/ssh/sshd_config.d/10-agentdeck.conf`).
- Root ha la password bloccata. Sullo schermo della Deck non c'è più il login di Linux: c'è l'attività
  dell'agente, comando per comando ([schermo.md](schermo.md)). Per farlo sshd imposta per `agent` solo la
  variabile `BASH_ENV`: autenticazione e permessi non cambiano.
- Nessun servizio esposto su internet senza una decisione esplicita (INV-5). L'unico esposto è SSH sulla porta
  49222, per la decisione del 26/10 (vedi "Da fuori casa"), con sshguard attivo.

## Snapshot

```bash
ssh agentdeck deck snapshot                                   # elenco, con in_grub per ognuno
ssh agentdeck 'deck snapshot create description="prima di X"'  # nuovo snapshot
```

Gli snapshot compaiono anche nel sottomenu "Arch Linux snapshots" di GRUB e si possono avviare in sola
lettura. Per tornare davvero a uno snapshot, da remoto e senza nessuno davanti alla Deck:

```bash
ssh agentdeck 'deck snapshot rollback id=N'                 # anteprima e codice di conferma
ssh agentdeck 'deck snapshot rollback id=N confirm=<codice>'  # esegue e riavvia
```

`deck` rifiuta gli snapshot da cui la Deck ripartirebbe senza accesso SSH o con un GRUB diverso. Dettagli
in [deck.md](deck.md).

## Se la Deck non risponde

1. **Verificare se è accesa e in rete:** `ping 192.168.1.49`; se non risponde, cercarla per nome con
   `dns-sd -G v4 agentdeck.local` (l'IP potrebbe essere cambiato).

   **Da fuori casa:**
   - `dig +short scarlethome.ddns.net` deve dare l'IP pubblico di casa;
   - `nc -z -G 5 scarlethome.ddns.net 49222` deve rispondere;
   - se il nome è giusto ma la porta non risponde, mancano la regola sul router o la Deck in rete;
   - se la porta risponde ma il collegamento si chiude subito, l'indirizzo da cui ti colleghi potrebbe essere
     bloccato da sshguard: da casa si controlla con `sudo nft list set ip sshguard attackers`.
2. **Se una modifica ha rotto qualcosa ma la Deck risponde:** `deck snapshot rollback` verso lo snapshot
   precedente alla modifica.
3. **Se un aggiornamento ha rotto l'avvio:** dal menu di GRUB si sceglie uno snapshot precedente oppure il
   kernel `linux-lts` in "Advanced options". Serve una persona davanti alla Deck.
4. **Se il sistema è irraggiungibile:** avviare la chiavetta di recupero (Volume giù + Accensione) e
   collegarsi con `ssh -i ~/.ssh/id_ed25519_steamdeck root@agentdeck-live.local`. Da lì si montano i
   subvolumi e si ripara. Vedi [chiavetta-live.md](chiavetta-live.md).
