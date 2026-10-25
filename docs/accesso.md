# Accesso alla Deck

Come l'agente raggiunge e gestisce la Deck, con quali protezioni, e cosa fare se non risponde.
Indice: [README.md](README.md).

## Collegarsi

Dal Mac basta:

```bash
ssh agentdeck
```

Le voci in `~/.ssh/config` del Mac:

```
Host agentdeck
  HostName 192.168.1.49
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

- `agentdeck` usa l'**IP stabile**: verificato con 10 collegamenti consecutivi riusciti al primo tentativo.
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

## Sicurezza

- SSH solo con chiave; password e accesso di root via SSH disattivati; unico utente ammesso `agent`
  (`/etc/ssh/sshd_config.d/10-agentdeck.conf`).
- Root ha la password bloccata. Il login che compare sullo schermo della Deck è la console di Linux: non
  serve a nessuno e resta lì finché non arriverà l'interfaccia grafica.
- Nessun servizio esposto su internet senza una decisione esplicita (INV-5).

## Snapshot

```bash
ssh agentdeck 'sudo snapper -c root list'
ssh agentdeck 'sudo snapper -c root create -d "descrizione"'
```

Gli snapshot compaiono anche nel sottomenu "Arch Linux snapshots" di GRUB e si possono avviare in sola
lettura. Un comando per tornare indietro (rollback) arriverà con il componente `deck snapshot`.

## Se la Deck non risponde

1. **Verificare se è accesa e in rete:** `ping 192.168.1.49`; se non risponde, cercarla per nome con
   `dns-sd -G v4 agentdeck.local` (l'IP potrebbe essere cambiato).
2. **Se un aggiornamento ha rotto l'avvio:** dal menu di GRUB si sceglie uno snapshot precedente oppure il
   kernel `linux-lts` in "Advanced options". Serve una persona davanti alla Deck.
3. **Se il sistema è irraggiungibile:** avviare la chiavetta di recupero (Volume giù + Accensione) e
   collegarsi con `ssh -i ~/.ssh/id_ed25519_steamdeck root@agentdeck-live.local`. Da lì si montano i
   subvolumi e si ripara. Vedi [chiavetta-live.md](chiavetta-live.md).
