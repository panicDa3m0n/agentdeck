#!/usr/bin/env bash
# Installa sulla Deck lo schermo "terminale dell'agente". Gira sulla Deck come root, lanciato da
# deck/install.sh dopo la copia in /opt/agentdeck. Ripetibile: cambia solo ciò che è diverso.
#
# Rete di sicurezza SSH (INV-1): se la configurazione SSH cambia, prima di ricaricare sshd viene programmato
# il ripristino automatico dopo 3 minuti. deck/install.sh prova ssh, scp e rsync e solo se funzionano
# annulla il ripristino (systemctl stop agentdeck-ssh-revert.timer).
#
# Documentazione: docs/schermo.md

set -euo pipefail

SRC=$(cd "$(dirname "$0")" && pwd)
LIB=/usr/local/lib/agentdeck
DROPIN=/etc/ssh/sshd_config.d/20-agentdeck-screen.conf
UNIT=/etc/systemd/system/agentdeck-screen.service

if ! cmp -s "$SRC/20-agentdeck-screen.conf" "$DROPIN" || ! cmp -s "$SRC/agentdeck-screen.service" "$UNIT"; then
  snapper -c root create -d "deck/screen: prima di modificare SSH o tty1"   # INV-3
fi

install -d -m 755 "$LIB"
install -m 644 "$SRC/ssh-log.sh" "$LIB/ssh-log.sh"
bash -n "$LIB/ssh-log.sh"

if ! cmp -s "$SRC/20-agentdeck-screen.conf" "$DROPIN"; then
  systemctl stop agentdeck-ssh-revert.timer 2>/dev/null || true
  systemd-run --quiet --on-active=180 --unit=agentdeck-ssh-revert \
    /bin/sh -c "rm -f $DROPIN && systemctl reload sshd"
  install -m 644 "$SRC/20-agentdeck-screen.conf" "$DROPIN"
  sshd -t
  systemctl reload sshd
  echo "SSH_CHANGED"
fi

if ! cmp -s "$SRC/agentdeck-screen.service" "$UNIT"; then
  install -m 644 "$SRC/agentdeck-screen.service" "$UNIT"
  systemctl daemon-reload
fi
systemctl mask --now getty@tty1.service >/dev/null 2>&1
systemctl enable agentdeck-screen.service >/dev/null 2>&1
systemctl restart agentdeck-screen.service
systemctl is-active agentdeck-screen.service
