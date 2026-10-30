# 02 Accesso e rete: i polmoni

**Stato:** attivo. Indice: [README.md](README.md).

## Scopo

Tenere l'agente collegato alla Deck in ogni momento (INV-1) e difendere la macchina verso l'esterno (INV-5). Se
questo organo si ferma, nessuno può più intervenire a distanza.

## Come funziona oggi

- **SSH:** solo con chiave, solo l'utente `agent`, niente root né password (INV-5). In casa: `ssh agentdeck`
  (`192.168.1.49`, prenotato sul router; mDNS `agentdeck.local`).
- **Da fuori casa:** `scarlethome.ddns.net:49222`, inoltrata dal router alla porta 22. È l'unico servizio esposto
  in modo permanente, per decisione del proprietario del 26/10 ([../accesso.md](../accesso.md)).
- **sshguard:** blocca nelle sue tabelle nftables chi sbaglia il login; non blocca mai la rete di casa.
- **Rete:** Wi-Fi con `iwd` (preferenza 5 GHz), DHCP con `systemd-networkd`, DNS e mDNS con `systemd-resolved`,
  LLMNR spento.
- **`deck network`:** interfacce, Wi-Fi, nomi e porte in ascolto. Azioni con anteprima e rete di sicurezza:
  `prefer_5ghz`, `keep_5ghz`, `llmnr_on`, `llmnr_off`, `scan`. Il cambio di Wi-Fi torna indietro da solo se non
  viene confermato ([../../deck/agentdeck/wifi_switch.py](../../deck/agentdeck/wifi_switch.py)).
- **Protezioni:** la guardia rifiuta stop, disable, mask e kill di `sshd`, `systemd-networkd`, `iwd`,
  `systemd-resolved` e `dbus-broker` ([../../deck/agentdeck/access.py](../../deck/agentdeck/access.py));
  `deck service` protegge gli stessi servizi.
- **Firewall:** nessuno. La politica di ingresso è `accept`; ci sono solo le tabelle di sshguard (verificato il 30/10).

## Comandi collegati

`deck network` (azioni `scan`, `prefer_5ghz`, `keep_5ghz`, `llmnr_on`, `llmnr_off`), `ssh agentdeck`,
`deck service show name=sshd`.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| IP stabile e SSH affidabile dal Mac | O1.T2, O1.T5 | ✔ |
| `deck network` con anteprima e rete di sicurezza (LLMNR, banda Wi-Fi) | O4 | ✔ |
| SSH da fuori casa con sshguard | O10.T5, O10.T10 | ✔ provato con la regola sul router |
| Ritorno al Wi-Fi a 5 GHz dopo il riavvio del router | O10.T11 | ✔ (trappola P22: aspettare qualche minuto) |
| sshguard protetto come l'accesso: regole, guardia, avviso in `deck status` | O12.T2 (N42) | ✖ |
| Il cambio di Wi-Fi ritenta prima di tornare indietro | O12.T3 (N49) | ✖ |
| Pacchetti dell'installazione allineati alla Deck (tmux, sshguard in `install.sh`) | O12.T4 (N28) | ✖ |
| Firewall nftables con rete di sicurezza che si annulla da sola | O13.T3, A3.1 | ✖ |
| Chiave dell'agente limitata alla rete di casa (`from=`) | A3.1 | ✖ previsto; da rivedere, perché oggi l'accesso da fuori casa è deciso |
| `deck access`: chiavi e `sshd` con rete di sicurezza | piano punto 4 | ✖ previsto, se serve davvero |

## Issue aperte

- Nessun firewall: ogni porta in ascolto è raggiungibile dalla LAN (per esempio la pagina dello schermo su
  `0.0.0.0:8777`, che il piano mette fuori ambito, punto 6).
- sshguard non è ancora fra i servizi protetti dalla guardia: fermarlo non è un rischio per l'accesso, ma toglie
  una difesa (N42).
- Il 30/10 la pagina di `deck secret` in rete di casa non raggiungeva il telefono del proprietario, anche se era sul
  Wi-Fi di casa. La causa non è stata cercata (dispositivo o router); le richieste usano il tunnel (componente 12).

## Obiettivi tecnici

1. O12.T2 e O12.T3, piccoli e già definiti.
2. Firewall nftables con rete di sicurezza (O13.T3): ingresso aperto solo per SSH, mDNS e le porte dei servizi decise.
