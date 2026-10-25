#!/usr/bin/env bash
# Avvio live di Arch sulla Steam Deck: collega il Wi-Fi, abilita SSH con la chiave dell'agente
# e mostra a schermo come raggiungere la macchina. Non tocca il disco interno.
# Lo esegue l'ISO ufficiale su tty1 grazie al parametro di boot script=.

set -u
AGENT_DIR=/run/archiso/bootmnt/agent
exec > >(tee -a /root/live-setup.log) 2>&1

say() { printf '\n== %s\n' "$*"; }

say "linuxai-steamdeck: preparazione ambiente live"

# Chiave SSH dell'agente: accesso a root solo con chiave (root nel live non ha password)
install -d -m 700 /root/.ssh
install -m 600 "$AGENT_DIR/authorized_keys" /root/.ssh/authorized_keys

# Nome raggiungibile dal Mac via mDNS: agentdeck-live.local
hostnamectl set-hostname agentdeck-live
install -d /etc/systemd/resolved.conf.d
printf '[Resolve]\nMulticastDNS=yes\n' > /etc/systemd/resolved.conf.d/mdns.conf
systemctl restart systemd-resolved

# Credenziali Wi-Fi lette alla lettera (niente virgolette o escape nel file)
WIFI_SSID=$(sed -n 's/^WIFI_SSID=//p' "$AGENT_DIR/wifi.env" | head -1)
WIFI_PASS=$(sed -n 's/^WIFI_PASS=//p' "$AGENT_DIR/wifi.env" | head -1)

# Lo script parte mentre il boot può essere ancora in corso: avvia esplicitamente iwd
systemctl start iwd
rfkill unblock wifi
dev=""
for _ in $(seq 1 30); do
  for d in /sys/class/net/*; do [[ -d $d/wireless ]] && dev=${d##*/}; done
  [[ -n $dev ]] && break
  sleep 1
done
[[ -z $dev ]] && { say "ERRORE: nessuna scheda Wi-Fi trovata"; exit 1; }

say "Connessione a '$WIFI_SSID' su $dev"
ip=""
for _ in $(seq 1 10); do
  iwctl station "$dev" scan; sleep 4
  iwctl --passphrase "$WIFI_PASS" station "$dev" connect "$WIFI_SSID"
  for _ in $(seq 1 20); do
    ip=$(ip -4 -o addr show "$dev" | awk '{print $4}' | cut -d/ -f1 | head -1)
    [[ -n $ip ]] && break 2
    sleep 1
  done
done
[[ -z $ip ]] && { say "ERRORE: Wi-Fi non connesso. Controlla secrets/wifi.env"; exit 1; }

resolvectl mdns "$dev" yes
systemctl start sshd

setfont ter-132b 2>/dev/null
cat <<EOF

  ======================================
    PRONTA - non serve fare altro
    IP:  $ip
    ssh root@agentdeck-live.local
  ======================================

EOF
