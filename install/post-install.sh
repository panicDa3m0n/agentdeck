#!/usr/bin/env bash
# Rifinitura dopo il primo avvio del sistema installato. Si esegue come "agent" via SSH:
#   ssh agentdeck 'bash -s' < install/post-install.sh
# Da lanciare solo dopo aver verificato che l'accesso SSH di "agent" funziona.
#
# Documentazione: docs/installazione.md

set -euo pipefail

echo "== Accesso root di riserva: rimosso"
sudo rm -f /root/.ssh/authorized_keys
sudo sed -i -E 's/^PermitRootLogin .*/PermitRootLogin no/; s/^AllowUsers .*/AllowUsers agent/' \
  /etc/ssh/sshd_config.d/10-agentdeck.conf
sudo sshd -t
sudo systemctl reload sshd
cat /etc/ssh/sshd_config.d/10-agentdeck.conf

echo "== GRUB: kernel principale come voce predefinita"
# con più kernel GRUB ordina i nomi dei file e sceglierebbe linux-lts come "il più recente"
sudo sed -i '/^GRUB_TOP_LEVEL=/d' /etc/default/grub
echo 'GRUB_TOP_LEVEL="/boot/vmlinuz-linux"' | sudo tee -a /etc/default/grub >/dev/null
sudo grub-mkconfig -o /boot/grub/grub.cfg 2>&1 | grep -E "^Found linux image|snapshot"
