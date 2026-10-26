#!/usr/bin/env bash
# Accesso alla Deck da fuori casa (task O10.T5). Si lancia dal Mac, dalla radice del repository:
#
#   bash install/remote-access.sh
#
# Sulla Deck: snapshot, sshguard installato e configurato (sshguard.conf, sshguard-whitelist), abilitato e avviato;
# poi tailscaled fermato e disabilitato, se c'è. sshd non cambia: resta solo chiave, solo l'utente agent.
# Il port forwarding (TCP 49222 esterna -> 192.168.1.49:22) sta sul router e lo crea l'utente dal suo pannello.
# Documentazione: docs/accesso.md
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

ssh agentdeck 'deck snapshot create "description=prima di sshguard (O10.T5)" >/dev/null && echo snapshot ok'
scp -q "$here/sshguard.conf" "$here/sshguard-whitelist" agentdeck:/tmp/
ssh agentdeck 'set -e
  pacman -Q sshguard >/dev/null 2>&1 || sudo pacman -S --needed --noconfirm sshguard
  sudo install -m 0644 /tmp/sshguard.conf /etc/sshguard.conf
  sudo install -d -m 0755 /etc/sshguard
  sudo install -m 0644 /tmp/sshguard-whitelist /etc/sshguard/whitelist
  rm -f /tmp/sshguard.conf /tmp/sshguard-whitelist
  sudo systemctl enable sshguard
  sudo systemctl restart sshguard
  if systemctl cat tailscaled.service >/dev/null 2>&1; then sudo systemctl disable --now tailscaled; fi
  sleep 2
  echo "sshguard: $(systemctl is-active sshguard)"
  sudo nft list chain ip sshguard blacklist >/dev/null && echo "firewall: tabella sshguard presente"
  echo "tailscaled: $(systemctl is-active tailscaled 2>/dev/null || true)"'
