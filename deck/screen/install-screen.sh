#!/usr/bin/env bash
# Installa sulla Deck lo schermo "terminale dell'agente". Gira sulla Deck come root, lanciato da
# deck/install.sh dopo la copia in /opt/agentdeck. Ripetibile: cambia solo ciò che è diverso.
#
# Rete di sicurezza SSH (INV-1): se cambiano la configurazione SSH o lo script di registrazione (che tocca
# l'input/output di ogni comando dell'agente), prima si salvano le versioni precedenti e si programma il
# loro ripristino automatico dopo 3 minuti. deck/install.sh prova ssh, scp, rsync, codici di uscita e dati
# binari e solo se tutto funziona annulla il ripristino (systemctl stop agentdeck-ssh-revert.timer).
#
# Documentazione: docs/schermo.md

set -euo pipefail

SRC=$(cd "$(dirname "$0")" && pwd)
LIB=/usr/local/lib/agentdeck
HOOK="$LIB/ssh-log.sh"
DROPIN=/etc/ssh/sshd_config.d/20-agentdeck-screen.conf
UNIT=/etc/systemd/system/agentdeck-screen.service
BACKUP="$LIB/previous"

ssh_changed=0
cmp -s "$SRC/ssh-log.sh" "$HOOK" || ssh_changed=1
cmp -s "$SRC/20-agentdeck-screen.conf" "$DROPIN" || ssh_changed=1

if [ "$ssh_changed" = 1 ] || ! cmp -s "$SRC/agentdeck-screen.service" "$UNIT"; then
  snapper -c root create -d "deck/screen: prima di modificare SSH o tty1"   # INV-3
fi

install -d -m 755 "$LIB"
if [ "$ssh_changed" = 1 ]; then
  # Versioni precedenti e script di ripristino: rimette ciò che c'era (o toglie ciò che non c'era)
  rm -rf "$BACKUP" && install -d -m 755 "$BACKUP"
  {
    echo '#!/bin/sh'
    for pair in "$HOOK:hook" "$DROPIN:dropin"; do
      target=${pair%%:*}; name=${pair#*:}
      if [ -e "$target" ]; then
        cp -p "$target" "$BACKUP/$name"
        echo "cp -p '$BACKUP/$name' '$target'"
      else
        echo "rm -f '$target'"
      fi
    done
    echo 'systemctl reload sshd'
  } > "$BACKUP/revert.sh"
  chmod 755 "$BACKUP/revert.sh"

  systemctl stop agentdeck-ssh-revert.timer 2>/dev/null || true
  systemd-run --quiet --on-active=180 --unit=agentdeck-ssh-revert "$BACKUP/revert.sh"

  install -m 644 "$SRC/ssh-log.sh" "$HOOK"
  bash -n "$HOOK"
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
